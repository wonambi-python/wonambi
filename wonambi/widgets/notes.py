# -*- coding: utf-8 -*-

"""Widgets containing notes (such as markers, events, and stages).

  - bookmarks are unique (might have the same text), are not mutually
    exclusive, have variable duration
  - events are not unique, are not mutually exclusive, have variable duration
  - stages are not unique, are mutually exclusive, have fixed duration


TODO:
    maybe it's better to disable options related to annotations, but it's a bit
    too complicated. If you do that, you can remove all "if self.annot is None"
    that are marked with "# remove if buttons are disabled"
"""
from datetime import datetime, timedelta
from functools import partial
from itertools import compress
from logging import getLogger
from numpy import (asarray, concatenate, diff, empty, floor, in1d, log, mean,
                   ptp, sqrt, square, std)
from scipy.signal import periodogram
from os.path import basename, splitext

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (QAbstractItemView,
                             QAction,
                             QCheckBox,
                             QComboBox,
                             QDialog,
                             QDialogButtonBox,
                             QFileDialog,
                             QFormLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QInputDialog,
                             QLabel,
                             QLineEdit,
                             QListWidget,
                             QListWidgetItem,
                             QMessageBox,
                             QPushButton,
                             QTableWidget,
                             QTableWidgetItem,
                             QTabWidget,
                             QVBoxLayout,
                             QWidget,
                             QScrollArea,
                             )

from .. import ChanTime
from ..trans import montage, filter_
from ..attr import Annotations, create_empty_annotations
from ..attr.annotations import create_annotation
from ..detect import DetectSpindle, DetectSlowWave, merge_close
from .settings import Config, FormStr, FormInt, FormFloat, FormBool
from .utils import convert_name_to_color, short_strings, ICON

lg = getLogger(__name__)

MAX_FREQUENCY_OF_INTEREST = 50
# TODO: this in ConfigNotes
STAGE_NAME = ['NREM1', 'NREM2', 'NREM3', 'REM', 'Wake', 'Movement',
              'Undefined', 'Unknown', 'Artefact', 'Unrecognized']
STAGE_SHORTCUT = ['1', '2', '3', '5', '9', '8', '0', '', '', '']
QUALIFIERS = ['Good', 'Poor']
QUALITY_SHORTCUT = ['o', 'p']
SPINDLE_METHODS = ['Wamsley2012', 'Nir2011', 'Moelle2011', 'Ferrarelli2007',
                   'UCSD']
SLOW_WAVE_METHODS = ['Massimini2004', 'AASM/Massimini2004']


class ConfigNotes(Config):
    """Widget with preferences in Settings window for the Annotations."""
    def __init__(self, update_widget):
        super().__init__('notes', update_widget)

    def create_config(self):

        box0 = QGroupBox('Markers')

        self.index['marker_show'] = FormBool('Display Markers in Dataset')
        self.index['marker_color'] = FormStr()
        self.index['annot_show'] = FormBool('Display User-Made Annotations')
        self.index['annot_bookmark_color'] = FormStr()
        self.index['min_marker_dur'] = FormFloat()

        form_layout = QFormLayout()
        form_layout.addRow(self.index['marker_show'])
        form_layout.addRow('Color of markers in the dataset',
                           self.index['marker_color'])
        form_layout.addRow(self.index['annot_show'])
        form_layout.addRow('Color of bookmarks in annotations',
                           self.index['annot_bookmark_color'])
        form_layout.addRow('Below this duration, markers and events have no '
                           'duration', self.index['min_marker_dur'])

        box0.setLayout(form_layout)

        box1 = QGroupBox('Events')

        form_layout = QFormLayout()
        box1.setLayout(form_layout)

        box2 = QGroupBox('Stages')

        self.index['scoring_window'] = FormInt()

        form_layout = QFormLayout()
        form_layout.addRow('Length of scoring window',
                           self.index['scoring_window'])
        box2.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addWidget(box1)
        main_layout.addWidget(box2)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


class Notes(QTabWidget):
    """Widget that contains information about sleep scoring.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    config : ConfigNotes
        preferences for this widget

    annot : Annotations
        contains the annotations made by the user

    idx_marker : QTableWidget
        table with the markers in the dataset

    idx_summary: QVBoxLayout
        layout of the "Summary" tab (we add and remove the "Recap" box)
    idx_annotations : QPushButton
        push button with the text of the annotation file
    idx_rater : QLabel
        name of the current rater
    idx_stats : QFormLayout
        layout of the stage statistics

    idx_eventtype_scroll : QScrollArea
        area to which you add the QGroupBox with the list of events as checkbox
    idx_eventtype_list : list of QCheckBox
        list of checkboxes with the event types
    idx_annot_list : QTableWidget
        table with the bookmarks and events in the annotations

    idx_eventtype : QComboBox
        Combo box of the event types for the toolbar
    idx_stage : QComboBox
        Combo box of the stages for the toolbar
    idx_quality : QComboBox
        Combo box of signal quality (good/poor) for the toolbar
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigNotes(self.update_settings)
        self.spindle_dialog = SpindleDialog(parent)

        self.annot = None
        self.data = None

        self.idx_marker = None

        self.idx_summary = None
        self.idx_annotations = None
        self.idx_rater = None
        self.idx_stats = None

        self.idx_eventtype_scroll = None
        self.idx_eventtype_list = []
        self.idx_annot_list = None

        self.idx_eventtype = None
        self.idx_stage = None
        self.idx_quality = None

        self.create()
        self.create_action()

    def create(self):
        """Create the widget layout with all the annotations."""

        """ ------ MARKERS ------ """
        tab0 = QTableWidget()
        self.idx_marker = tab0

        tab0.setColumnCount(3)
        tab0.horizontalHeader().setStretchLastSection(True)
        tab0.setSelectionBehavior(QAbstractItemView.SelectRows)
        tab0.setEditTriggers(QAbstractItemView.NoEditTriggers)
        go_to_marker = lambda r, c: self.go_to_marker(r, c, 'dataset')
        tab0.cellDoubleClicked.connect(go_to_marker)
        tab0.setHorizontalHeaderLabels(['Start', 'Duration', 'Text'])

        """ ------ SUMMARY ------ """
        tab1 = QWidget()
        self.idx_eventtype = QComboBox(self)
        self.idx_stage = QComboBox(self)
        self.idx_stage.activated.connect(self.get_sleepstage)
        self.idx_quality = QComboBox(self)
        self.idx_quality.activated.connect(self.get_quality)

        self.idx_annotations = QPushButton('Load Annotation File...')
        self.idx_annotations.clicked.connect(self.load_annot)
        self.idx_rater = QLabel('')

        b0 = QGroupBox('Info')
        form = QFormLayout()
        b0.setLayout(form)

        form.addRow('File:', self.idx_annotations)
        form.addRow('Rater:', self.idx_rater)

        b1 = QGroupBox('Staging')
        b2 = QGroupBox('Signal quality')

        layout = QVBoxLayout()
        layout.addWidget(b0)
        layout.addWidget(b1)
        layout.addWidget(b2)
        self.idx_summary = layout

        tab1.setLayout(layout)

        """ ------ ANNOTATIONS ------ """
        tab2 = QWidget()
        tab_annot = QTableWidget()
        self.idx_annot_list = tab_annot
        delete_row = QPushButton('Delete')
        delete_row.clicked.connect(self.delete_row)

        scroll = QScrollArea(tab2)
        scroll.setWidgetResizable(True)

        evttype_group = QGroupBox('Event Types')
        scroll.setWidget(evttype_group)
        self.idx_eventtype_scroll = scroll

        tab_annot.setColumnCount(5)
        tab_annot.setHorizontalHeaderLabels(['Start', 'Duration', 'Text',
                                             'Type', 'Channel'])
        tab_annot.horizontalHeader().setStretchLastSection(True)
        tab_annot.setSelectionBehavior(QAbstractItemView.SelectRows)
        tab_annot.setEditTriggers(QAbstractItemView.NoEditTriggers)
        go_to_annot = lambda r, c: self.go_to_marker(r, c, 'annot')
        tab_annot.cellDoubleClicked.connect(go_to_annot)

        layout = QVBoxLayout()
        layout.addWidget(self.idx_eventtype_scroll, stretch=1)
        layout.addWidget(self.idx_annot_list)
        layout.addWidget(delete_row)
        tab2.setLayout(layout)

        """ ------ TABS ------ """
        self.addTab(tab0, 'Markers')
        self.addTab(tab1, 'Summary')  # disable
        self.addTab(tab2, 'Annotations')  # disable

    def create_action(self):
        """Create actions associated with Annotations."""
        actions = {}

        act = QAction('New Annotations', self)
        act.triggered.connect(self.new_annot)
        actions['new_annot'] = act

        act = QAction('Load Annotations', self)
        act.triggered.connect(self.load_annot)
        actions['load_annot'] = act

        act = QAction('Clear Annotations...', self)
        act.triggered.connect(self.clear_annot)
        actions['clear_annot'] = act

        act = QAction('New...', self)
        act.triggered.connect(self.new_rater)
        actions['new_rater'] = act

        act = QAction('Delete...', self)
        act.triggered.connect(self.delete_rater)
        actions['del_rater'] = act

        act = QAction(QIcon(ICON['bookmark']), 'New Bookmark', self)
        act.setCheckable(True)
        actions['new_bookmark'] = act

        act = QAction(QIcon(ICON['new_eventtype']), 'New Event Type', self)
        act.triggered.connect(self.new_eventtype)
        actions['new_eventtype'] = act

        act = QAction(QIcon(ICON['del_eventtype']), 'Delete Event Type', self)
        act.triggered.connect(self.delete_eventtype)
        actions['del_eventtype'] = act

        act = QAction('Merge Events...', self)
        act.triggered.connect(self.parent.show_merge_dialog)
        act.setEnabled(False)
        actions['merge_events'] = act

        act = QAction(QIcon(ICON['event']), 'Event Mode', self)
        act.setCheckable(True)
        actions['new_event'] = act

        uncheck_new_event = lambda: actions['new_event'].setChecked(False)
        uncheck_new_bookmark = lambda: actions['new_bookmark'].setChecked(False)
        actions['new_event'].triggered.connect(uncheck_new_bookmark)
        actions['new_bookmark'].triggered.connect(uncheck_new_event)

        act = {}
        for one_stage, one_shortcut in zip(STAGE_NAME, STAGE_SHORTCUT):
            act[one_stage] = QAction('Score as ' + one_stage, self.parent)
            act[one_stage].setShortcut(one_shortcut)
            stage_idx = STAGE_NAME.index(one_stage)
            act[one_stage].triggered.connect(partial(self.get_sleepstage,
                                                     stage_idx))
            self.addAction(act[one_stage])

        actions['stages'] = act

        act = {}
        for one_qual, one_shortcut in zip(QUALIFIERS, QUALITY_SHORTCUT):
            act[one_qual] = QAction('Score as ' + one_qual, self.parent)
            act[one_qual].setShortcut(one_shortcut)
            qual_idx = QUALIFIERS.index(one_qual)
            act[one_qual].triggered.connect(partial(self.get_quality,
                                                    qual_idx))
            self.addAction(act[one_qual])

        actions['quality'] = act

        act = QAction('Set cycle start', self)
        act.triggered.connect(self.get_cycle_mrkr)
        actions['cyc_start'] = act

        act = QAction('Set cycle end', self)
        act.triggered.connect(partial(self.get_cycle_mrkr, end=True))
        actions['cyc_end'] = act

        act = QAction('Remove cycle marker', self)
        act.triggered.connect(self.remove_cycle_mrkr)
        actions['remove_cyc'] = act

        act = QAction('Clear cycle markers', self)
        act.triggered.connect(self.clear_cycle_mrkrs)
        actions['clear_cyc'] = act

        act = QAction('Domino', self)
        act.triggered.connect(partial(self.import_staging, 'domino'))
        actions['import_domino'] = act

        act = QAction('Alice', self)
        act.triggered.connect(partial(self.import_staging, 'alice'))
        actions['import_alice'] = act

        act = QAction('Sandman', self)
        act.triggered.connect(partial(self.import_staging, 'sandman'))
        actions['import_sandman'] = act

        act = QAction('RemLogic', self)
        act.triggered.connect(partial(self.import_staging, 'remlogic'))
        actions['import_remlogic'] = act

        act = QAction('Compumedics', self)
        act.triggered.connect(partial(self.import_staging, 'compumedics'))
        actions['import_compumedics'] = act

        act = QAction('FASST', self)
        act.triggered.connect(self.import_fasst)
        actions['import_fasst'] = act

        act = QAction('Export staging', self)
        act.triggered.connect(self.export)
        actions['export'] = act

        act = QAction('Spindle...', self)
        act.triggered.connect(self.parent.show_spindle_dialog)
        act.setEnabled(False)
        actions['spindle'] = act

        act = QAction('Slow wave...', self)
        act.triggered.connect(self.parent.show_slow_wave_dialog)
        act.setEnabled(False)
        actions['slow_wave'] = act

        act = QAction('Events...', self)
        act.triggered.connect(self.parent.show_event_analysis_dialog)
        act.setEnabled(False)
        actions['analyze_events'] = act

        act = QAction('Analysis... (coming soon)', self)
        act.triggered.connect(self.parent.show_analysis_dialog)
        act.setEnabled(False)
        actions['analyze'] = act

        self.action = actions

    def update_settings(self):
        """Once Settings are applied, update the notes."""
        self.update_dataset_marker()
        self.update_annotations()

    def update_notes(self, xml_file, new=False):
        """Update information about the sleep scoring.

        Parameters
        ----------
        xml_file : str
            file of the new or existing .xml file
        new : bool
            if the xml_file should be a new file or an existing one
        """
        if new:
            create_empty_annotations(xml_file, self.parent.info.dataset)
            self.annot = Annotations(xml_file)
        else:
            self.annot = Annotations(xml_file)

        self.action['merge_events'].setEnabled(True)
        self.action['spindle'].setEnabled(True)
        self.action['slow_wave'].setEnabled(True)
        self.action['analyze_events'].setEnabled(True)
        #self.action['analyze'].setEnabled(True)
        self.parent.create_menubar()
        self.idx_stage.clear()
        for one_stage in STAGE_NAME:
            self.idx_stage.addItem(one_stage)
        self.idx_stage.setCurrentIndex(-1)
        self.idx_quality.clear()
        for one_qual in QUALIFIERS:
            self.idx_quality.addItem(one_qual)
        self.idx_quality.setCurrentIndex(-1)

        w1 = self.idx_summary.takeAt(1).widget()
        w2 = self.idx_summary.takeAt(1).widget()
        self.idx_summary.removeWidget(w1)
        self.idx_summary.removeWidget(w2)
        w1.deleteLater()
        w2.deleteLater()

        b1 = QGroupBox('Staging')

        layout = QFormLayout()
        for one_stage in STAGE_NAME:
            layout.addRow(one_stage, QLabel(''))
        b1.setLayout(layout)
        self.idx_summary.addWidget(b1)
        self.idx_stage_stats = layout

        b2 = QGroupBox('Signal quality')

        layout = QFormLayout()
        for one_qual in QUALIFIERS:
            layout.addRow(one_qual, QLabel(''))
        b2.setLayout(layout)
        self.idx_summary.addWidget(b2)
        self.idx_qual_stats = layout

        self.display_notes()

    def display_notes(self):
        """Display information about scores and raters.
        """
        if self.annot is not None:
            short_xml_file = short_strings(basename(self.annot.xml_file))
            self.idx_annotations.setText(short_xml_file)
            # if annotations were loaded without dataset
            if self.parent.overview.scene is None:
                self.parent.overview.update()

            if not self.annot.raters:
                self.new_rater()

            self.idx_rater.setText(self.annot.current_rater)
            self.display_eventtype()
            self.update_annotations()
            self.display_stats()

    def display_stats(self):
        """Display summary statistics about duration in each stage."""
        for i, one_stage in enumerate(STAGE_NAME):
            second_in_stage = self.annot.time_in_stage(one_stage)
            time_in_stage = str(timedelta(seconds=second_in_stage))

            label = self.idx_stage_stats.itemAt(i,
                                                QFormLayout.FieldRole).widget()
            label.setText(time_in_stage)

        for i, one_qual in enumerate(QUALIFIERS):
            second_in_qual = self.annot.time_in_stage(one_qual, attr='quality')
            time_in_qual = str(timedelta(seconds=second_in_qual))

            label = self.idx_qual_stats.itemAt(i,
                                               QFormLayout.FieldRole).widget()
            label.setText(time_in_qual)

    def add_bookmark(self, time):
        """Run this function when user adds a new bookmark.

        Parameters
        ----------
        time : tuple of float
            start and end of the new bookmark, in s
        """
        if self.annot is None:  # remove if buttons are disabled
            msg = 'No score file loaded'
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)
            return

        answer = QInputDialog.getText(self, 'New Bookmark',
                                      'Enter bookmark\'s name')
        if answer[1]:
            name = answer[0]
            self.annot.add_bookmark(name, time)
            lg.info('Added Bookmark ' + name + 'at ' + str(time))

        self.update_annotations()

    def update_dataset_marker(self):
        """Update markers which are in the dataset. It always updates the list
        of events. Depending on the settings, it might add the markers to
        overview and traces.
        """
        start_time = self.parent.overview.start_time

        markers = []
        if self.parent.info.markers is not None:
            markers = self.parent.info.markers

        self.idx_marker.clearContents()
        self.idx_marker.setRowCount(len(markers))

        for i, mrk in enumerate(markers):
            abs_time = (start_time +
                        timedelta(seconds=mrk['start'])).strftime('%H:%M:%S')
            dur = timedelta(seconds=mrk['end'] - mrk['start'])
            duration = '{0:02d}.{1:03d}'.format(dur.seconds,
                                                round(dur.microseconds / 1000))

            item_time = QTableWidgetItem(abs_time)
            item_duration = QTableWidgetItem(duration)
            item_name = QTableWidgetItem(mrk['name'])

            color = self.parent.value('marker_color')
            item_time.setForeground(QColor(color))
            item_duration.setForeground(QColor(color))
            item_name.setForeground(QColor(color))

            self.idx_marker.setItem(i, 0, item_time)
            self.idx_marker.setItem(i, 1, item_duration)
            self.idx_marker.setItem(i, 2, item_name)

        # store information about the time as list (easy to access)
        marker_start = [mrk['start'] for mrk in markers]
        self.idx_marker.setProperty('start', marker_start)

        if self.parent.traces.data is not None:
            self.parent.traces.display()
        self.parent.overview.display_markers()

    def display_eventtype(self):
        """Read the list of event types in the annotations and update widgets.
        """
        if self.annot is not None:
            event_types = sorted(self.annot.event_types, key=str.lower)
        else:
            event_types = []

        self.idx_eventtype.clear()

        evttype_group = QGroupBox('Event Types')
        layout = QVBoxLayout()
        evttype_group.setLayout(layout)

        self.idx_eventtype_list = []
        for one_eventtype in event_types:
            self.idx_eventtype.addItem(one_eventtype)
            item = QCheckBox(one_eventtype)
            layout.addWidget(item)
            item.setCheckState(Qt.Checked)
            item.stateChanged.connect(self.update_annotations)
            self.idx_eventtype_list.append(item)

        self.idx_eventtype_scroll.setWidget(evttype_group)

    def get_selected_events(self, time_selection=None):
        """Returns which events are present in one time window.

        Parameters
        ----------
        time_selection : tuple of float
            start and end of the window of interest

        Returns
        -------
        list of dict
            list of events in the window of interest
        """
        events = []
        for checkbox in self.idx_eventtype_list:
            if checkbox.checkState() == Qt.Checked:
                events.extend(self.annot.get_events(name=checkbox.text(),
                                                    time=time_selection))

        return events

    def update_annotations(self):
        """Update annotations made by the user, including bookmarks and events.
        Depending on the settings, it might add the bookmarks to overview and
        traces.
        """
        start_time = self.parent.overview.start_time

        if self.parent.notes.annot is None:
            all_annot = []
        else:
            bookmarks = self.parent.notes.annot.get_bookmarks()
            events = self.get_selected_events()

            all_annot = bookmarks + events
            all_annot = sorted(all_annot, key=lambda x: x['start'])

        self.idx_annot_list.clearContents()
        self.idx_annot_list.setRowCount(len(all_annot))

        for i, mrk in enumerate(all_annot):
            abs_time = (start_time +
                        timedelta(seconds=mrk['start'])).strftime('%H:%M:%S')
            dur = timedelta(seconds=mrk['end'] - mrk['start'])
            duration = '{0:02d}.{1:03d}'.format(dur.seconds,
                                                round(dur.microseconds / 1000))

            item_time = QTableWidgetItem(abs_time)
            item_duration = QTableWidgetItem(duration)
            item_name = QTableWidgetItem(mrk['name'])
            if mrk in bookmarks:
                item_type = QTableWidgetItem('bookmark')
                color = self.parent.value('annot_bookmark_color')
            else:
                item_type = QTableWidgetItem('event')
                color = convert_name_to_color(mrk['name'])
            chan = mrk['chan']
            if isinstance(chan, (tuple, list)):
                chan = ', '.join(chan)
            item_chan = QTableWidgetItem(chan)

            item_time.setForeground(QColor(color))
            item_duration.setForeground(QColor(color))
            item_name.setForeground(QColor(color))
            item_type.setForeground(QColor(color))
            item_chan.setForeground(QColor(color))

            self.idx_annot_list.setItem(i, 0, item_time)
            self.idx_annot_list.setItem(i, 1, item_duration)
            self.idx_annot_list.setItem(i, 2, item_name)
            self.idx_annot_list.setItem(i, 3, item_type)
            self.idx_annot_list.setItem(i, 4, item_chan)

        # store information about the time as list (easy to access)
        annot_start = [ann['start'] for ann in all_annot]
        annot_end = [ann['end'] for ann in all_annot]
        self.idx_annot_list.setProperty('start', annot_start)
        self.idx_annot_list.setProperty('end', annot_end)

        if self.parent.traces.data is not None:
            self.parent.traces.display_annotations()
        self.parent.overview.display_annotations()

    def delete_row(self):
        """Delete bookmarks or event from annotations, based on row."""
        sel_model = self.idx_annot_list.selectionModel()
        for row in sel_model.selectedRows():
            i = row.row()
            start = self.idx_annot_list.property('start')[i]
            end = self.idx_annot_list.property('end')[i]
            name = self.idx_annot_list.item(i, 2).text()
            marker_event = self.idx_annot_list.item(i, 3).text()
            if marker_event == 'bookmark':
                self.annot.remove_bookmark(name=name, time=(start, end))
            else:
                self.annot.remove_event(name=name, time=(start, end))

        self.update_annotations()

    def go_to_marker(self, row, col, table_type):
        """Move to point in time marked by the marker.

        Parameters
        ----------
        row : QtCore.int

        column : QtCore.int

        table_type : str
            'dataset' table or 'annot' table, it works on either
        """
        if table_type == 'dataset':
            marker_time = self.idx_marker.property('start')[row]
        else:
            marker_time = self.idx_annot_list.property('start')[row]

        window_length = self.parent.value('window_length')
        window_start = floor(marker_time / window_length) * window_length
        self.parent.overview.update_position(window_start)

    def get_sleepstage(self, stage_idx=None):
        """Get the sleep stage, using shortcuts or combobox."""
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        scoring_window = self.parent.value('scoring_window')

        if window_length != scoring_window:
            msg = ('Zoom to ' + str(scoring_window) + ' (epoch length) ' +
                   'for sleep scoring.')
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)
            return

        try:
            self.annot.set_stage_for_epoch(window_start,
                                           STAGE_NAME[stage_idx])

        except KeyError:
            msg = ('The start of the window does not correspond to any epoch ' +
                   'in sleep scoring file')
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)

        else:
            lg.debug('User staged ' + str(window_start) + ' as ' +
                     STAGE_NAME[stage_idx])

            self.set_stage_index()
            self.parent.overview.mark_stages(window_start, window_length,
                                             STAGE_NAME[stage_idx])
            self.display_stats()
            self.parent.traces.page_next()

    def get_quality(self, qual_idx=None):
        """Get the signal qualifier, using shortcuts or combobox."""
        if self.annot is None:  # remove if buttons are disabled
            msg = 'No score file loaded'
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)
            return

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')

        try:
            self.annot.set_stage_for_epoch(window_start,
                                           QUALIFIERS[qual_idx],
                                           attr='quality')

        except KeyError:
            msg = ('The start of the window does not correspond to any epoch ' +
                   'in sleep scoring file')
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)

        else:
            lg.debug('User staged ' + str(window_start) + ' as ' +
                     QUALIFIERS[qual_idx])

            self.set_quality_index()
            self.parent.overview.mark_quality(window_start, window_length,
                                              QUALIFIERS[qual_idx])
            self.display_stats()
            self.parent.traces.page_next()

    def get_cycle_mrkr(self, end=False):
        """Mark cycle start or end.

        Parameters
        ----------
        end : bool
            If True, marks a cycle end; otherwise, it's a cycle start
        """
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')

        try:
            self.annot.set_cycle_mrkr(window_start, end=end)

        except KeyError:
            msg = ('The start of the window does not correspond to any epoch ' +
                   'in sleep scoring file')
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)

        else:
            bound = 'start'
            if end:
                bound = 'end'
            lg.info('User marked ' + str(window_start) + ' as cycle ' +
                    bound)

            self.parent.overview.mark_cycles(window_start, window_length,
                                             end=end)

    def remove_cycle_mrkr(self):
        """Remove cycle marker."""
        window_start = self.parent.value('window_start')

        try:
            self.annot.remove_cycle_mrkr(window_start)

        except KeyError:
            msg = ('The start of the window does not correspond to any cycle ' +
                   'marker in sleep scoring file')
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)

        else:
            lg.debug('User removed cycle marker at' + str(window_start))
            #self.trace
            self.parent.overview.update(reset=False)
            self.parent.overview.display_annotations()

    def clear_cycle_mrkrs(self, test=False):
        """Remove all cycle markers."""
        if not test:
            msgBox = QMessageBox(QMessageBox.Question, 'Clear Cycle Markers',
                                 'Are you sure you want to remove all cycle '
                                 'markers for this rater?')
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgBox.setDefaultButton(QMessageBox.Yes)
            response = msgBox.exec_()

            if response == QMessageBox.No:
                return

        self.annot.clear_cycles()

        self.parent.overview.display()
        self.parent.overview.display_annotations()

    def set_stage_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        stage = self.annot.get_stage_for_epoch(window_start, window_length)
        lg.info('winstart: ' + str(window_start) + ', stage: ' + str(stage))

        if stage is None:
            self.idx_stage.setCurrentIndex(-1)
        else:
            self.idx_stage.setCurrentIndex(STAGE_NAME.index(stage))

    def set_quality_index(self):
        """Set the current signal quality in combobox."""
        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        qual = self.annot.get_stage_for_epoch(window_start, window_length,
                                              attr='quality')
        lg.info('winstart: ' + str(window_start) + ', quality: ' + str(qual))

        if qual is None:
            self.idx_quality.setCurrentIndex(-1)
        else:
            self.idx_quality.setCurrentIndex(QUALIFIERS.index(qual))

    def new_annot(self):
        """Action: create a new file for annotations."""
        if self.parent.info.filename is None:
            msg = 'No dataset loaded'
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)
            return

        filename = splitext(self.parent.info.filename)[0] + '_scores.xml'
        filename, _ = QFileDialog.getSaveFileName(self, 'Create annotation file',
                                                  filename,
                                                  'Annotation File (*.xml)')
        if filename == '':
            return

        self.update_notes(filename, True)

    def load_annot(self):
        """Action: load a file for annotations."""
        if self.parent.info.filename is not None:
            filename = splitext(self.parent.info.filename)[0] + '_scores.xml'
        else:
            filename = None

        filename, _ = QFileDialog.getOpenFileName(self, 'Load annotation file',
                                                  filename,
                                                  'Annotation File (*.xml)')

        if filename == '':
            return

        try:
            self.update_notes(filename, False)
        except FileNotFoundError:
            msg = 'Annotation file not found'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)

    def clear_annot(self):
        """Action: clear all the annotations (ask for confirmation first)."""
        msgBox = QMessageBox(QMessageBox.Question, 'Clear Annotations',
                             'Do you want to remove all the annotations?')
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgBox.setDefaultButton(QMessageBox.Yes)
        response = msgBox.exec_()

        if response == QMessageBox.No:
            return

        self.reset()

    def import_fasst(self, checked=False, test_fasst=None, test_annot=None):
        """Action: import from FASST .mat file"""

        if self.parent.info.filename is not None:
            fasst_file = splitext(self.parent.info.filename)[0] + '.mat'
            annot_file = splitext(self.parent.info.filename)[0] + '_scores.xml'
        else:
            fasst_file = annot_file = ''

        if test_fasst is None:
            fasst_file, _ = QFileDialog.getOpenFileName(self, 'Load FASST score file',
                                                        fasst_file,
                                                        'FASST score file (*.mat)')
        else:
            fasst_file = test_fasst

        if fasst_file == '':
            return

        if test_annot is None:
            annot_file, _ = QFileDialog.getSaveFileName(self, 'Create annotation file',
                                                        annot_file,
                                                        'Annotation File (*.xml)')
        else:
            annot_file = test_annot

        if annot_file == '':
            return

        try:
            create_annotation(annot_file, from_fasst=fasst_file)
        except BaseException as err:
            self.parent.statusBar().showMessage(str(err))
            lg.info(str(err))
            return

        try:
            self.update_notes(annot_file, False)
        except FileNotFoundError:
            msg = 'Annotation file not found'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)

    def import_staging(self, source, staging_start=None, test_filename=None,
                       test_rater=None):
        """Action: import an external sleep staging file.

        Parameters
        ----------
        source : str
            Name of program where staging was exported. One of 'alice',
            'compumedics', 'domino', 'remlogic', 'sandman'.
        staging_start : datetime, optional
            Absolute time when staging begins.
        """
        if self.annot is None:  # remove if buttons are disabled
            msg = 'No score file loaded'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)
            return

        if self.parent.info.dataset is None:
            msg = 'No dataset loaded'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)
            return

        record_start = self.parent.info.dataset.header['start_time']

        if test_filename is None:
            filename, _ = QFileDialog.getOpenFileName(self,
                                                      'Load staging file',
                                                      None,
                                                      'Text File (*.txt)')
        else:
            filename = test_filename

        if filename == '':
            return

        if test_rater is None:
            rater, ok = QInputDialog.getText(self, 'Import staging',
                                          'Enter rater name')
            if not ok:
                return

            if rater in self.annot.raters:
                msgBox = QMessageBox(QMessageBox.Question, 'Overwrite staging',
                                     'Rater %s already exists. \n \n'
                                     'Overwrite %s\'s sleep staging '
                                     'with imported staging? Events '
                                     'and bookmarks will be preserved.'
                                     % (rater, rater))
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msgBox.setDefaultButton(QMessageBox.No)
                response = msgBox.exec_()

                if response == QMessageBox.No:
                    return
        else:
            rater = test_rater

        if source == 'compumedics':
            time_str, ok = QInputDialog.getText(self, 'Staging start time',
                                                'Enter date and time when '
                                                'staging \nbegins, using '
                                                '24-hour clock. \n\nFormat: '
                                                'YYYY,MM,DD HH:mm:SS')
            if not ok:
                return

            try:
                staging_start = datetime.strptime(time_str,
                                                  '%Y,%m,%d %H:%M:%S')
            except (ValueError, TypeError) as e:
                msg = 'Incorrect formatting for date and time.'
                self.parent.statusBar().showMessage(msg)
                lg.info(msg)
                return

        try:
            self.annot.import_staging(filename, source, rater,
                                      record_start,
                                      staging_start=staging_start)
        except FileNotFoundError:
            msg = 'File not found'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)

        self.display_notes()
        self.parent.create_menubar()  # refresh list ot raters

    def new_rater(self):
        """Action: add a new rater.

        Notes
        -----
        First argument, if not specified, is a bool/False:
        http://pyqt.sourceforge.net/Docs/PyQt4/qaction.html#triggered
        """
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        answer = QInputDialog.getText(self, 'New Rater',
                                      'Enter rater\'s name')
        if answer[1]:
            self.annot.add_rater(answer[0],
                                 self.parent.value('scoring_window'))
            self.display_notes()
            self.parent.create_menubar()  # refresh list ot raters

    def select_rater(self, rater=False):
        """Action: select one rater.

        Parameters
        ----------
        rater : str
            name of the rater
        """
        self.annot.get_rater(rater)
        self.display_notes()
        self.set_stage_index()
        self.set_quality_index()

    def delete_rater(self):
        """Action: create dialog to delete rater."""
        answer = QInputDialog.getText(self, 'Delete Rater',
                                      'Enter rater\'s name')
        if answer[1]:
            self.annot.remove_rater(answer[0])
            self.display_notes()
            self.parent.create_menubar()  # refresh list ot raters

    def new_eventtype(self, test_type_str=None):
        """Action: create dialog to add new event type."""
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        if test_type_str:
            answer = test_type_str, True
        else:
            answer = QInputDialog.getText(self, 'New Event Type',
                                          'Enter new event\'s name')
        if answer[1]:
            self.annot.add_event_type(answer[0])
            self.display_eventtype()
            n_eventtype = self.idx_eventtype.count()
            self.idx_eventtype.setCurrentIndex(n_eventtype - 1)

    def delete_eventtype(self, test_type_str=None):
        """Action: create dialog to delete event type."""
        if test_type_str:
            answer = test_type_str, True
        else:
            answer = QInputDialog.getText(self, 'Delete Event Type',
                                          'Enter event\'s name to delete')
        if answer[1]:
            self.annot.remove_event_type(answer[0])
            self.display_eventtype()

    def add_event(self, name, time, chan):
        """Action: add a single event."""
        self.annot.add_event(name, time, chan=chan)
        self.update_annotations()

    def remove_event(self, name=None, time=None, chan=None):
        """Action: remove single event."""
        self.annot.remove_event(name=name, time=time, chan=chan)
        self.update_annotations()

    def read_data(self, chan, group, stage=None, quality=None):
        """Read the data to analyze.
        # TODO: make times more flexible (see below)
        Parameters
        ----------
        chan : str or list of str
            Channel(s) to read.
        group : dict
            Channel group, for information about referencing, filtering, etc.
        stage : tuple of str, optional
            stage(s) of interest
        quality : str, optional
            only include epochs of this signal quality
        """
        if isinstance(chan, str):
            chan = [chan]

        dataset = self.parent.info.dataset

        chan_to_read = chan + group['ref_chan']

        data = dataset.read_data(chan=chan_to_read)

        max_s_freq = self.parent.value('max_s_freq')
        if data.s_freq > max_s_freq:
            q = int(data.s_freq / max_s_freq)
            lg.debug('Decimate (no low-pass filter) at ' + str(q))

            data.data[0] = data.data[0][:, slice(None, None, q)]
            data.axis['time'][0] = data.axis['time'][0][slice(None, None, q)]
            data.s_freq = int(data.s_freq / q)

        times = None
        if stage or quality:
            times = []
            stage_cond = True
            qual_cond = True

            for ep in self.annot.epochs:
                if stage:
                    stage_cond = ep['stage'] in stage
                if quality:
                    qual_cond = ep['quality'] == quality
                if stage_cond and qual_cond:
                    times.append((ep['start'], ep['end']))

            if len(times) == 0:
                self.parent.statusBar().showMessage('No valid epochs found.')
                self.data = None
                return

        self.data = _create_data_to_analyze(data, chan, group, times=times)

    def detect_events(self, method, params, label):
        """Detect events and display on signal.

        Parameters
        ----------
        method : str
            Method used for detection.
        params : dict
            Parameters used for detection.
        label : str
            Name of event type, on event labels
        """
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        lg.info('Adding event type ' + label)
        self.annot.add_event_type(label)
        self.display_eventtype()
        n_eventtype = self.idx_eventtype.count()
        self.idx_eventtype.setCurrentIndex(n_eventtype - 1)

        freq = (float(params['f1']), float(params['f2']))
        lg.info('freq: ' + str(freq))
        duration = (params['min_dur'], params['max_dur'])

        if method in SPINDLE_METHODS:
            detector = DetectSpindle(method=method, frequency=freq,
                                     duration=duration, merge=params['merge'])

            if method in ['Wamsley2012', 'UCSD']:
                detector.det_wavelet['dur'] = params['win_sz']
            else:
                detector.moving_rms['dur'] = params['win_sz']

            detector.det_wavelet['sd'] = params['sigma']
            detector.smooth['dur'] = params['smooth']
            detector.det_thresh = params['det_thresh']
            detector.sel_thresh = params['sel_thresh']
            detector.min_interval = params['interval']

        elif method in SLOW_WAVE_METHODS:
            lg.info('building SW detector with ' + method)
            detector = DetectSlowWave(method=method, duration=duration)

            detector.det_filt['freq'] = freq
            detector.trough_duration = (params['min_trough_dur'],
                                        params['max_trough_dur'])
            detector.max_trough_amp = params['max_trough_amp']
            detector.min_ptp = params['min_ptp']
            detector.invert = params['invert']

        else:
            lg.info('Method not recognized: ' + method)
            return

        events = detector(self.data)

        for one_ev in events:
            self.annot.add_event(label,(one_ev['start'],
                                        one_ev['end']),
                                        chan=one_ev['chan'])

        self.update_annotations()

    def analyze_events(self, event_type, chan, stage, params, frequency,
                       cycles=None, fsplit=None):
        """Compute parameters on events. Only supports one trial.

        Parameters
        ----------
        event_type : str
            name of event type to analyze
        chan : str or tuple of str
            channel where event data are retrieved
        stage :
            stage(s) of interest; events in other stages will be ignored.
            If None, all events will be analyzed.
        params : list
            list of parameters to compute.
        frequency : tuple of float
            frequencies for filtering.
        cycles: list of tuple, optional
            start and end times of cycles, in seconds from recording start
        fsplit : float, optional
            peak frequency at which to split the event dataset

        Returns
        -------
        list of dict
            Parameter name as key with global parameters/avgs as values. If
            fsplit, there are two dicts, low frequency and high frequency
            respectively, combined together in a list.
        list of list of dict
            One dictionary per event, each containing  individual event
            parameters. If fsplit, there are two event lists, low frequency
            and high frequency respectively, combined together in a list.
            Otherwise, there is a single list within the master list.
        """
        events = [self.annot.get_events(
                    name=event_type, chan=chan, stage=stage, qual='Good')]
        summary = []
        f1 = frequency[0]
        f2 = frequency[1]
        filtered = None
        diff_dat = None
        s_freq = self.data.s_freq

        if 'density' in params:
            epochs = self.annot.epochs

            if stage is None:
                n_epochs = len([x for x in epochs])
            else:
                n_epochs = len([x for x in epochs if x['stage'] in stage])

        if in1d(['maxamp', 'ptp', 'rms'], params).any():
            filtered = filter_(self.data,
                               low_cut=f1, high_cut=f2)(chan=chan)[0]

        if in1d(['peakf', 'power', 'rms'], params).any():
            diff_dat = diff(self.data(chan=chan)[0])

        per_evt_params = ['dur', 'peakf', 'maxamp', 'ptp', 'rms', 'power']
        per_evt_cond = in1d(per_evt_params, params)
        sel_params = list(compress(per_evt_params, per_evt_cond))

        if per_evt_cond.any():

            for ev in events[0]:
                start = max(int(ev['start'] * s_freq), 0)
                end = min(int(ev['end'] * s_freq),
                          len(self.data(chan=chan)[0]))

                if start >= end:
                    lg.warning('Event at %(start)f - %(end)f is size zero' %
                            {'start': start, 'end':end})
                    continue

                if 'dur' in params:
                    ev['dur'] = ev['end'] - ev['start']

                if filtered is not None:
                    one_evt = filtered[start:end]

                    if 'maxamp' in params:
                        ev['maxamp'] = one_evt.max()

                    if 'ptp' in params:
                        ev['ptp'] = ptp(one_evt)

                    if 'rms' in params:
                        ev['rms'] = sqrt(mean(square(diff(one_evt))))

                if diff_dat is not None:
                    one_evt = diff_dat[start:end]
                    sf, Pxx = periodogram(one_evt, self.data.s_freq)
                    # find nearest frequency to f1 and f2 in sf
                    b0 = asarray([abs(x - f1) for x in sf]).argmin()
                    b1 = asarray([abs(x - f2) for x in sf]).argmin()

                    if 'peakf' in params:
                        idx_peak = Pxx[b0:b1].argmax()
                        ev['peakf'] = sf[b0:b1][idx_peak]

                    if 'power' in params:
                        ev['power'] = mean(Pxx[b0:b1])

                if 'log' in params:
                    for param in sel_params:
                        ev[param] = log(ev[param])

            if cycles:
                all_events = []

                for cyc in cycles:
                    evts_in_cyc = [ev for ev in events[0] \
                                   if cyc[0] <= ev['start'] < cyc[1]]
                    all_events.append(evts_in_cyc)

                events = all_events

            if fsplit:
                if 'log' in params:
                    fsplit = log(fsplit)
                all_events = []

                for evs in events:
                    events_lo = [ev for ev in evs if ev['peakf'] < fsplit]
                    events_hi = [ev for ev in evs if ev['peakf'] >= fsplit]
                    all_events.extend([events_lo, events_hi])

                events = all_events

        for evs in events:
            summ = {}

            if 'count' in params:
                summ['count'] = (len(evs),)

            if 'density' in params:
                summ['density'] = (len(evs) / n_epochs,)

            if 'log' in params:
                summ = {k: log(v) for (k, v) in summ.items()}

            if per_evt_cond.any():
                for param in sel_params:
                    dat = [ev[param] for ev in evs]
                    summ[param] = mean(dat), std(dat)

            summary.append(summ)

        if per_evt_cond.any():
            evt_output = events
        else:
            evt_output = [None]

        return summary, evt_output

    def export(self):
        """action: export annotations to CSV."""
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        filename = splitext(self.annot.xml_file)[0] + '.csv'
        filename, _ = QFileDialog.getSaveFileName(self, 'Export stages',
                                                  filename,
                                                  'Sleep stages (*.csv)')
        if filename == '':
            return

        self.annot.export(filename)

    def reset(self):
        """Remove all annotations from window."""
        self.idx_annotations.setText('Load Annotation File...')
        self.idx_rater.setText('')

        self.annot = None
        self.dataset_markers = None

        # remove dataset marker
        self.idx_marker.clearContents()
        self.idx_marker.setRowCount(0)

        # remove summary statistics
        w1 = self.idx_summary.takeAt(1).widget()
        w2 = self.idx_summary.takeAt(1).widget()
        self.idx_summary.removeWidget(w1)
        self.idx_summary.removeWidget(w2)
        w1.deleteLater()
        w2.deleteLater()
        b1 = QGroupBox('Staging')
        b2 = QGroupBox('Signal quality')
        self.idx_summary.addWidget(b1)
        self.idx_summary.addWidget(b2)

        # remove annotations
        self.display_eventtype()
        self.update_annotations()

        self.parent.create_menubar()  # remove all raters


class ChannelDialog(QDialog):
    """Template dialog for event detection.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window
    group : dict
        information about groups from Channels
    index : dict of FormFloat
        Contains detection parameters.

    bbox : QDialogButtonBox
        Button box with Help, Ok and Cancel
    idx_group : QComboBox
        Combo box of channel groups.
    idx_chan : QListWidget
        List widget containing all channels for selected group.
    """
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent

        self.setWindowModality(Qt.ApplicationModal)
        self.groups = self.parent.channels.groups
        self.index = {}

        self.create_basic_dialog()

    def create_basic_dialog(self):
        self.bbox = QDialogButtonBox(QDialogButtonBox.Help |
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_help = self.bbox.button(QDialogButtonBox.Help)
        self.idx_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = self.bbox.button(QDialogButtonBox.Cancel)

        chan_grp_box = QComboBox()
        for gr in self.groups:
            chan_grp_box.addItem(gr['name'])
        self.idx_group = chan_grp_box
        chan_grp_box.activated.connect(self.update_channels)

        chan_box = QListWidget()
        self.idx_chan = chan_box

        stage_box = QListWidget()
        stage_box.addItems(STAGE_NAME)
        stage_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_stage = stage_box

    def update_groups(self):
        """Update the channel groups list when dialog is opened."""
        self.groups = self.parent.channels.groups
        self.idx_group.clear()
        for gr in self.groups:
            self.idx_group.addItem(gr['name'])

        self.update_channels()

    def update_channels(self):
        """Update the channels list when a new group is selected."""
        group_dict = {k['name']: i for i, k in enumerate(self.groups)}
        group_index = group_dict[self.idx_group.currentText()]
        self.one_grp = self.groups[group_index]

        self.idx_chan.clear()

        self.idx_chan.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for chan in self.one_grp['chan_to_plot']:
            name = chan + '—(' + '+'.join(self.one_grp['ref_chan']) + ')'
            item = QListWidgetItem(name)
            self.idx_chan.addItem(item)

    def get_channels(self):
        """Get the selected channel(s in order). """
        selectedItems = self.idx_chan.selectedItems()
        selected_chan = [x.text().split('—')[0] for x in selectedItems]
        chan_in_order = []
        for chan in self.one_grp['chan_to_plot']:
            if chan in selected_chan:
                chan_in_order.append(chan)

        return chan_in_order

class SpindleDialog(ChannelDialog):
    """Dialog for specifying spindle detection parameters, ie:
    label, channel, stage, lowcut, highcut, min dur, max dur, detection method,
    wavelet sigma, detection window, smoothing, detection threshold, selection
    threshold, minimum interval, merge across channels.

    Attributes
    ----------
    label : str
        name of event type (to be added to or created)
    method : str
        name of detection method
    idx_method : QComboBox
        Combo box of detection methods.
    """
    def __init__(self, parent):
        ChannelDialog.__init__(self, parent)
        self.setWindowTitle('Spindle detection')
        self.method = None
        self.idx_method = None

        self.create_dialog()

    def create_dialog(self):
        """ Create the dialog."""
        box0 = QGroupBox('Info')

        self.label = FormStr()
        self.index['merge'] = FormBool('Merge events across channels')

        self.label.setText('spin')
        self.idx_chan.itemSelectionChanged.connect(self.count_channels)
        self.index['merge'].setCheckState(Qt.Unchecked)
        self.index['merge'].setEnabled(False)

        form_layout = QFormLayout()
        box0.setLayout(form_layout)
        form_layout.addRow('Label',
                           self.label)
        form_layout.addRow('Channel group',
                           self.idx_group)
        form_layout.addRow('Channel(s)',
                           self.idx_chan)
        form_layout.addRow('Stage(s)',
                           self.idx_stage)
        form_layout.addRow(self.index['merge'])

        box1 = QGroupBox('General parameters')

        self.index['f1'] = FormFloat()
        self.index['f2'] = FormFloat()
        self.index['min_dur'] = FormFloat()
        self.index['max_dur'] = FormFloat()

        self.index['f1'].set_value(10.)
        self.index['f2'].set_value(16.)
        self.index['min_dur'].set_value(0.5)
        self.index['max_dur'].set_value(3.)

        form_layout = QFormLayout()
        box1.setLayout(form_layout)
        form_layout.addRow('Lowcut (Hz)',
                           self.index['f1'])
        form_layout.addRow('Highcut (Hz)',
                           self.index['f2'])
        form_layout.addRow('Minimum duration (s)',
                           self.index['min_dur'])
        form_layout.addRow('Maximum duration (s)',
                           self.index['max_dur'])

        box2 = QGroupBox('Method parameters')

        mbox = QComboBox()
        method_list = SPINDLE_METHODS
        for method in method_list:
            mbox.addItem(method)
        self.idx_method = mbox
        self.method = mbox.currentText()
        mbox.currentIndexChanged.connect(self.update_values)

        self.index['sigma'] = FormFloat()
        self.index['win_sz'] = FormFloat()
        self.index['smooth'] = FormFloat()
        self.index['det_thresh'] = FormFloat()
        self.index['sel_thresh'] = FormFloat()
        self.index['interval'] = FormFloat()

        form_layout = QFormLayout()
        box2.setLayout(form_layout)
        form_layout.addRow('Method',
                            mbox)
        form_layout.addRow('Wavelet sigma',
                           self.index['sigma'])
        form_layout.addRow('Detection window',
                           self.index['win_sz'])
        form_layout.addRow('Smoothing',
                           self.index['smooth'])
        form_layout.addRow('Detection threshold',
                           self.index['det_thresh'])
        form_layout.addRow('Selection threshold',
                           self.index['sel_thresh'])
        form_layout.addRow('Minimum interval',
                           self.index['interval'])

        self.bbox.clicked.connect(self.button_clicked)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(box0)
        vlayout.addWidget(box1)
        vlayout.addWidget(box2)
        vlayout.addStretch(1)
        vlayout.addLayout(btnlayout)

        self.update_values()
        self.setLayout(vlayout)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            chans = self.get_channels()
            stage = self.idx_stage.selectedItems()
            params = {k: v.get_value() for k, v in self.index.items()}

            if None in [params['f1'], params['f2']]:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            if params['max_dur'] is None:
                self.parent.statusBar().showMessage('Specify maximum duration')
                return
            elif params['max_dur'] >= 30:
                self.parent.statusBar().showMessage(
                        'Maximum duration must be below 30 seconds.')
                return

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]
            lg.info('chans= '+str(chans)+' stage= '+str(stage)+' grp= '+str(self.one_grp))

            self.parent.notes.read_data(chans, self.one_grp, stage=stage,
                                        quality='Good')
            if self.parent.notes.data is not None:
                self.parent.notes.detect_events(self.method, params,
                                                label=self.label.get_value())

            self.accept()

        if button is self.idx_cancel:
            self.reject()

        if button is self.idx_help:
            self.parent.show_spindle_help()

    def update_values(self):
        """Update form values when detection method is selected."""
        self.method = self.idx_method.currentText()
        spin_det = DetectSpindle(method=self.method)

        if self.method in ['Wamsley2012', 'UCSD']:
            self.index['win_sz'].set_value(spin_det.det_wavelet['dur'])
        else:
            self.index['win_sz'].set_value(spin_det.moving_rms['dur'])

        self.index['sigma'].set_value(spin_det.det_wavelet['sd'])
        self.index['smooth'].set_value(spin_det.smooth['dur'])
        self.index['det_thresh'].set_value(spin_det.det_thresh)
        self.index['sel_thresh'].set_value(spin_det.sel_thresh)
        self.index['interval'].set_value(spin_det.min_interval)

        for param in ['sigma', 'win_sz', 'det_thresh', 'sel_thresh', 'smooth']:
            widg = self.index[param]
            if widg.get_value() == 0:
                widg.set_value('N/A')
                widg.setEnabled(False)
            else:
                widg.setEnabled(True)

    def count_channels(self):
        """If more than one channel selected, activate merge checkbox."""
        merge = self.index['merge']

        if len(self.idx_chan.selectedItems()) > 1:
            if merge.isEnabled():
                return
            else:
                merge.setEnabled(True)
                merge.setCheckState(Qt.Checked)
        else:
            self.index['merge'].setCheckState(Qt.Unchecked)
            self.index['merge'].setEnabled(False)


class SWDialog(ChannelDialog):
    """Dialog for specifying SW detection parameters, ie:
    label, channel, stage, min dur, max dur, detection method, lowcut, highcut,
    minimum and maximum trough duration, maximum trough amplitude, minimum
    peak-to-peak amplitude.

    Attributes
    ----------
    label : str
        name of event type (to be added to or created)
    method : str
        name of detection method
    idx_method : QComboBox
        Combo box of detection methods.
    """
    def __init__(self, parent):
        ChannelDialog.__init__(self, parent)
        self.setWindowTitle('Slow wave detection')
        self.idx_method = None

        self.create_dialog()

    def create_dialog(self):
        """ Create the dialog."""
        box0 = QGroupBox('Info')

        self.label = FormStr()
        self.index['invert'] = FormBool('Invert detection')

        self.label.setText('sw')
        self.index['invert'].setCheckState(Qt.Unchecked)

        form_layout = QFormLayout()
        box0.setLayout(form_layout)
        form_layout.addRow('Label',
                           self.label)
        form_layout.addRow('Channel group',
                           self.idx_group)
        form_layout.addRow('Channel(s)',
                           self.idx_chan)
        form_layout.addRow('Stage(s)',
                           self.idx_stage)
        form_layout.addRow(self.index['invert'])

        box1 = QGroupBox('General parameters')

        self.index['min_dur'] = FormFloat()
        self.index['max_dur'] = FormFloat()

        self.index['min_dur'].set_value(0.5)
        self.index['max_dur'].set_value(3.)

        form_layout = QFormLayout()
        box1.setLayout(form_layout)
        form_layout.addRow('Minimum duration (s)',
                           self.index['min_dur'])
        form_layout.addRow('Maximum duration (s)',
                           self.index['max_dur'])

        box2 = QGroupBox('Method parameters')

        mbox = QComboBox()
        method_list = SLOW_WAVE_METHODS
        for method in method_list:
            mbox.addItem(method)
        self.idx_method = mbox
        self.method = mbox.currentText()
        mbox.currentIndexChanged.connect(self.update_values)

        self.index['f1'] = FormFloat()
        self.index['f2'] = FormFloat()
        self.index['min_trough_dur'] = FormFloat()
        self.index['max_trough_dur'] = FormFloat()
        self.index['max_trough_amp'] = FormFloat()
        self.index['min_ptp'] = FormFloat()

        form_layout = QFormLayout()
        box2.setLayout(form_layout)
        form_layout.addRow('Method',
                            mbox)
        form_layout.addRow('Lowcut (Hz)',
                           self.index['f1'])
        form_layout.addRow('Highcut (Hz)',
                           self.index['f2'])
        form_layout.addRow('Minimum trough duration (s)',
                           self.index['min_trough_dur'])
        form_layout.addRow('Maximum trough duration (s)',
                           self.index['max_trough_dur'])
        form_layout.addRow('Maximum trough amplitude (uV)',
                           self.index['max_trough_amp'])
        form_layout.addRow('Minimum peak-to-peak amplitude (uV)',
                           self.index['min_ptp'])

        self.bbox.clicked.connect(self.button_clicked)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(box0)
        vlayout.addWidget(box1)
        vlayout.addWidget(box2)
        vlayout.addStretch(1)
        vlayout.addLayout(btnlayout)

        self.update_values()
        self.setLayout(vlayout)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            chans = self.get_channels()
            stage = self.idx_stage.selectedItems()
            params = {k: v.get_value() for k, v in self.index.items()}

            if None in [params['f1'], params['f2']]:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]

            self.parent.notes.read_data(chans, self.one_grp, stage=stage,
                                        quality='Good')

            if self.parent.notes.data is not None:
                self.parent.notes.detect_events(self.method, params,
                                                label=self.label.get_value())

            self.accept()

        if button is self.idx_cancel:
            self.reject()

        if button is self.idx_help:
            self.parent.show_slowwave_help()
            pass

    def update_values(self):
        """Update form values when detection method is selected."""
        self.method = self.idx_method.currentText()
        sw_det = DetectSlowWave(method=self.method)

        self.index['f1'].set_value(sw_det.det_filt['freq'][0])
        self.index['f2'].set_value(sw_det.det_filt['freq'][1])
        self.index['min_trough_dur'].set_value(sw_det.trough_duration[0])
        self.index['max_trough_dur'].set_value(sw_det.trough_duration[1])
        self.index['max_trough_amp'].set_value(sw_det.max_trough_amp)
        self.index['min_ptp'].set_value(sw_det.min_ptp)

        """
        for param in ['sigma', 'win_sz', 'det_thresh', 'sel_thresh', 'smooth']:
            widg = self.index[param]
            if widg.get_value() == 0:
                widg.set_value('N/A')
                widg.setEnabled(False)
            else:
                widg.setEnabled(True)
        """


class MergeDialog(QDialog):
    """Dialog for specifying which events to merge. Events are merged when
    less than a minimum interval separates them. Events can be within-channel
    only or both within- and across-channel. Merged to channel with longest
    event.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window
    idx_evt_type : QListWidget
        List of event types.
    min_interval : FormFloat
        Events separated by this value (in seconds) or less are merged.
    cross_chan: FormBool
        For cross-channel merging.
    """
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent

        self.setWindowTitle('Merge events')
        self.setWindowModality(Qt.ApplicationModal)

        self.create_dialog()

    def create_dialog(self):
        """ Create the dialog."""
        box0 = QGroupBox('Info')

        event_box = QListWidget()
        event_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_evt_type = event_box

        mbox = QComboBox()
        mlist = ['earlier onset event', 'longer duration event']
        for m in mlist:
            mbox.addItem(m)
        self.idx_merge_to = mbox
        self.merge_to = mbox.currentText()

        self.min_interval = FormFloat()
        self.cross_chan = FormBool('Merge across channels')

        self.min_interval.set_value(1.0)
        self.cross_chan.setCheckState(Qt.Checked)

        form_layout = QFormLayout()
        box0.setLayout(form_layout)
        form_layout.addRow('Event type(s)',
                           self.idx_evt_type)
        form_layout.addRow(self.cross_chan)
        form_layout.addRow('Merge to...',
                           self.idx_merge_to)
        form_layout.addRow('Minimum interval (sec)',
                           self.min_interval)

        bbox = QDialogButtonBox(QDialogButtonBox.Help |
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_help = bbox.button(QDialogButtonBox.Help)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)
        bbox.clicked.connect(self.button_clicked)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(box0)
        vlayout.addStretch(1)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            evt_types = [x.text() for x in self.idx_evt_type.selectedItems()]
            self.merge_to = self.idx_merge_to.currentText()
            min_interval = self.min_interval.get_value()
            events = []
            merge_to_longer = False

            if not evt_types:
                QMessageBox.warning(self, 'Missing information',
                                     'Choose at least one event type.')
                return

            if not min_interval:
                QMessageBox.warning(self, 'Missing information',
                                     'Choose a minimum interval.')
                return


            if self.merge_to == 'longer duration event':
                merge_to_longer = True

            if len(evt_types) > 1:
                answer = QInputDialog.getText(self, 'New Event Type',
                                      'Enter new event\'s name')

                if answer[1]:
                    name = answer[0]

                else:
                    return

            else:
                name = evt_types[0]

            for etype in evt_types:
                events.extend(self.parent.notes.annot.get_events(name=etype,
                                                                 qual='Good'))

            if self.cross_chan.get_value():
                events = merge_close(events, min_interval,
                                     merge_to_longer=merge_to_longer)

            else:
                channels = set([x['chan'] for x in events])
                events = []
                chan_events = []

                for chan in channels:

                    for etype in evt_types:

                        chan_events.extend(self.parent.notes.annot.get_events(
                                name=etype, chan=chan, qual='Good'))

                    events.extend(merge_close(chan_events, min_interval,
                                              merge_to_longer=merge_to_longer))

            for etype in evt_types:
                self.parent.notes.annot.remove_event_type(etype)

            for ev in events:
                self.parent.notes.add_event(name, (ev['start'], ev['end']),
                                            ev['chan'])

            self.parent.notes.display_eventtype()
            n_eventtype = self.parent.notes.idx_eventtype.count()
            self.parent.notes.idx_eventtype.setCurrentIndex(n_eventtype - 1)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

        if button is self.idx_help:
            #self.parent.show_merge_help()
            pass

    def update_event_types(self):
        """Update event types in event type box."""
        self.idx_evt_type.clear()
        self.idx_evt_type.setSelectionMode(QAbstractItemView.ExtendedSelection)
        event_types = sorted(self.parent.notes.annot.event_types,
                             key=str.lower)

        for ty in event_types:
            item = QListWidgetItem(ty)
            self.idx_evt_type.addItem(item)


class EventAnalysisDialog(QDialog):
    """Dialog for specifying event analysis measures

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window
    group : dict
        information about groups from Channels
    index : dict of FormBool
        Contains information about parameters to analyze, for analyze_events.
    frequency : dict of FormFloat
        Contains lowcut and highcut frequencies for bandpassing.
    filename : str
        path/name of file to create
    cycles : list of tuple
        cycle start and end times, in seconds from recording start

    idx_evt_type : QComboBox
        Combo box of event types.
    idx_group : QComboBox
        Combo box of channel groups.
    idx_chan : QComboBox
        Combo box of all channels for selected group.
    """
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent

        self.setWindowTitle('Event analysis')
        self.setWindowModality(Qt.ApplicationModal)
        self.groups = self.parent.channels.groups
        self.idx_group = None
        self.idx_chan = None
        self.event_types = None
        self.idx_evt_type = None
        self.filename = None
        self.index = {}
        self.frequency = {}
        self.cycles = None

        self.create_dialog()

    def create_dialog(self):
        """ Create the dialog."""
        bbox = QDialogButtonBox(QDialogButtonBox.Help | QDialogButtonBox.Ok |
                QDialogButtonBox.Cancel)
        self.idx_help = bbox.button(QDialogButtonBox.Help)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)
        bbox.clicked.connect(self.button_clicked)

        box0 = QGroupBox('Info')

        filebutton = QPushButton()
        filebutton.setText('Choose')
        filebutton.clicked.connect(self.save_as)
        self.idx_filename = filebutton

        event_box = QComboBox()
        if self.event_types is not None:
            for ev in self.event_types:
                event_box.addItem(ev)
        self.idx_evt_type = event_box

        chan_grp_box = QComboBox()
        for gr in self.groups:
            chan_grp_box.addItem(gr['name'])
        self.idx_group = chan_grp_box
        chan_grp_box.activated.connect(self.update_channels)

        chan_box = QComboBox()
        self.idx_chan = chan_box

        stage_box = QListWidget()
        stage_box.addItems(STAGE_NAME)
        stage_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_stage = stage_box

        form_layout = QFormLayout()
        box0.setLayout(form_layout)
        form_layout.addRow('Filename',
                            self.idx_filename)
        form_layout.addRow('Event type',
                            self.idx_evt_type)
        form_layout.addRow('Channel group',
                            self.idx_group)
        form_layout.addRow('Channel',
                            self.idx_chan)
        form_layout.addRow('Stage(s)',
                            self.idx_stage)

        boxfilt = QGroupBox('Bandpass')

        self.frequency['locut'] = FormFloat()
        self.frequency['hicut'] = FormFloat()

        self.frequency['locut'].set_value(10)
        self.frequency['hicut'].set_value(16)

        form_layout = QFormLayout()
        boxfilt.setLayout(form_layout)
        form_layout.addRow('Lowcut (Hz)',
                            self.frequency['locut'])
        form_layout.addRow('Highcut (Hz)',
                            self.frequency['hicut'])

        box1 = QGroupBox('Parameters, global')

        self.index['count'] = FormBool('Count')
        self.index['density'] = FormBool('Density, per epoch of stage(s)')

        self.index['count'].setCheckState(Qt.Checked)
        self.index['density'].setCheckState(Qt.Checked)

        form_layout = QFormLayout()
        box1.setLayout(form_layout)
        form_layout.addRow(self.index['count'])
        form_layout.addRow(self.index['density'])

        box2 = QGroupBox('Parameters, per event')

        self.index['dur'] = FormBool('Duration (s)')
        self.index['maxamp'] = FormBool('Maximum amplitude (uV)')
        self.index['ptp'] = FormBool('Peak-to-peak amplitude (uV)')
        self.index['peakf'] = FormBool('Peak frequency (Hz)')
        self.index['power'] = FormBool('Average power (uV^2)')
        self.index['rms'] = FormBool('RMS (uV)')

        self.index['dur'].setCheckState(Qt.Checked)
        self.index['maxamp'].setCheckState(Qt.Checked)
        self.index['ptp'].setCheckState(Qt.Checked)
        self.index['peakf'].setCheckState(Qt.Checked)
        self.index['power'].setCheckState(Qt.Checked)
        self.index['rms'].setCheckState(Qt.Checked)

        form_layout = QFormLayout()
        box2.setLayout(form_layout)
        form_layout.addRow(self.index['dur'])
        form_layout.addRow(self.index['maxamp'])
        form_layout.addRow(self.index['ptp'])
        form_layout.addRow(self.index['peakf'])
        form_layout.addRow(self.index['power'])
        form_layout.addRow(self.index['rms'])

        box3 = QGroupBox('Options')

        self.index['log'] = FormBool('Log transform all')
        self.freq_split = FormBool('Frequency split')
        self.cyc_split = FormBool('Cycle split')
        self.freq_cutoff = QLineEdit()

        self.index['log'].setCheckState(Qt.Unchecked)
        self.freq_split.setCheckState(Qt.Unchecked)
        self.freq_split.stateChanged.connect(self.update_fsplit)
        self.freq_cutoff.setEnabled(False)
        self.cyc_split.setCheckState(Qt.Unchecked)

        fslayout = QHBoxLayout()
        fslayout.addWidget(self.freq_split)
        fslayout.addWidget(self.freq_cutoff)

        form_layout = QFormLayout()
        box3.setLayout(form_layout)
        form_layout.addRow(self.index['log'])
        form_layout.addRow(fslayout)
        form_layout.addRow(self.cyc_split)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(box0)
        vlayout.addWidget(boxfilt)
        vlayout.addWidget(box1)
        vlayout.addWidget(box2)
        vlayout.addWidget(box3)
        vlayout.addStretch(1)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            if self.filename is None:
                return

            freqs = (self.frequency['locut'].get_value(),
                     self.frequency['hicut'].get_value())

            if None in freqs:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            filename = self.filename
            evt_type = self.idx_evt_type.currentText()
            chan = self.idx_chan.currentText()
            chan_name = chan + ' (' + self.idx_group.currentText() + ')'
            params = [k for k, v in self.index.items() if v.get_value()]
            stage = self.idx_stage.selectedItems()
            lg.info('stage: ' + str(stage))
            cycles = None
            fsplit = None

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]

            if self.cyc_split.get_value():
                cycles = self.cycles

            if self.freq_split.get_value():
                fsplit = float(self.freq_cutoff.text())

            self.parent.notes.read_data(chan, self.one_grp)

            summary, events = self.parent.notes.analyze_events(evt_type,
                                                             chan_name,
                                                             stage,
                                                             params,
                                                             frequency=freqs,
                                                             cycles=cycles,
                                                             fsplit=fsplit)

            self.parent.notes.annot.export_event_data(filename, summary,
                                                      events, cycles=cycles,
                                                      fsplit=fsplit)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

        if button is self.idx_help:
            self.parent.show_evt_analysis_help()

    def save_as(self):
        """Dialog for getting name, location of annotation export csv."""
        filename = splitext(
                self.parent.notes.annot.xml_file)[0] + '_event_data.csv'
        filename, _ = QFileDialog.getSaveFileName(self, 'Export event data',
                                                  filename,
                                                  'Sleep stages (*.csv)')
        if filename == '':
            return

        self.filename = filename
        short_filename = short_strings(basename(self.filename))
        self.idx_filename.setText(short_filename)

    def update_types(self):
        """Update the event types list when dialog is opened."""
        self.event_types = self.parent.notes.annot.event_types
        self.idx_evt_type.clear()
        for ev in self.event_types:
            self.idx_evt_type.addItem(ev)

    def update_groups(self):
        """Update the channel groups list when dialog is opened."""
        self.groups = self.parent.channels.groups
        self.idx_group.clear()
        for gr in self.groups:
            self.idx_group.addItem(gr['name'])

        self.update_channels()

    def update_channels(self):
        """Update the channels list when a new group is selected."""
        group_dict = {k['name']: i for i, k in enumerate(self.groups)}
        group_index = group_dict[self.idx_group.currentText()]
        self.one_grp = self.groups[group_index]

        self.idx_chan.clear()

        for chan in self.one_grp['chan_to_plot']:
            self.idx_chan.addItem(chan)

    def update_cycles(self):
        """Enable cycles checkbox only if there are cycles marked, with no
        errors."""
        try:
            self.cycles = self.parent.notes.annot.get_cycles()

        except ValueError as msg:
            self.cyc_split.setEnabled(False)
            self.parent.statusBar().showMessage('There is a problem with the '
                                 'cycle markers: ' + str(msg))

        else:
            if self.cycles is None:
                self.cyc_split.setEnabled(False)
            else:
                self.cyc_split.setEnabled(True)

    def update_fsplit(self):
        """Enable/disable power lowcut and highcut rows."""
        if self.freq_split.get_value() == True:
            self.freq_cutoff.setEnabled(True)
            self.index['peakf'].set_value(True)
            self.index['peakf'].setEnabled(False)
        else:
            self.freq_cutoff.setEnabled(False)
            self.index['peakf'].setEnabled(True)


def _create_data_to_analyze(data, analysis_chans, chan_grp, times):
    """Create data after montage and filtering.

    Parameters
    ----------
    data : instance of ChanTime
        the raw data
    analysis_chans : list of str
        the channel(s) of interest and their reference(s), if any
    chan_grp : dict
        information about channels to plot, to use as reference and about
        filtering etc.
    times : list of tuple
        start and end time(s); several in case of epoch concatenation. times
        are in seconds from recording start.

    Returns
    -------
    instance of ChanTime
        data ready to be analyzed. one trial only.

    """
    s_freq = data.s_freq

    if times is None:
        times = [(None, None)]
    else:
        times = [(int(t0 * s_freq), int(t1 * s_freq)) for (t0, t1) in times]

    output = ChanTime()
    output.s_freq = s_freq
    #output.start_time = data.start_time   #not sure what this is used for
    output.axis['chan'] = empty(1, dtype='O')
    output.axis['time'] = empty(1, dtype='O')
    output.data = empty(1, dtype='O')

    all_epoch_data = []
    clock_time = []
    all_chan_grp_name = []

    for chan in analysis_chans:
        chan_grp_name = chan + ' (' + chan_grp['name'] + ')'
        all_chan_grp_name.append(chan_grp_name)

    sel_data = _select_channels(data,
                                analysis_chans +
                                chan_grp['ref_chan'])
    data1 = montage(sel_data, ref_chan=chan_grp['ref_chan'])

    for (t0, t1) in times:
        one_interval = data.axis['time'][0][t0: t1]
        clock_time.append(one_interval)
        epoch_dat = empty((len(analysis_chans), len(one_interval)))
        i_ch = 0

        for chan in analysis_chans:
            dat = data1(chan=chan, trial=0)
            #dat = dat - nanmean(dat)
            epoch_dat[i_ch, :] = dat[t0: t1]
            i_ch += 1

        all_epoch_data.append(epoch_dat)

    output.axis['chan'][0] = asarray(all_chan_grp_name, dtype='U')
    output.axis['time'][0] = concatenate(clock_time)
    output.data[0] = concatenate(all_epoch_data, axis=1)

    return output

def _select_channels(data, channels):
    """Select channels.

    Parameters
    ----------
    data : instance of ChanTime
        data with all the channels
    channels : list
        channels of interest

    Returns
    -------
    instance of ChanTime
        data with only channels of interest

    Notes
    -----
    This function does the same as sleepytimes.trans.select, but it's much faster.
    sleepytimes.trans.Select needs to flexible for any data type, here we assume
    that we have one trial, and that channel is the first dimension.

    """
    output = data._copy()
    chan_list = list(data.axis['chan'][0])
    idx_chan = [chan_list.index(i_chan) for i_chan in channels]
    output.data[0] = data.data[0][idx_chan, :]
    output.axis['chan'][0] = asarray(channels)

    return output
