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
from logging import getLogger
from numpy import asarray, floor
from os.path import basename, splitext
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (QAbstractItemView,
                             QAction,
                             QCheckBox,
                             QComboBox,
                             QDialog,
                             QDialogButtonBox,
                             QErrorMessage,
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
                             QProgressDialog,
                             QPushButton,
                             QSpinBox,
                             QTableWidget,
                             QTableWidgetItem,
                             QTabWidget,
                             QVBoxLayout,
                             QWidget,
                             QScrollArea,
                             )

from .. import ChanTime
from ..attr import Annotations, create_empty_annotations
from ..attr.annotations import create_annotation
from ..detect import DetectSpindle, DetectSlowWave, merge_close
from ..ioeeg import _write_vmrk
from .settings import Config
from .utils import (convert_name_to_color, FormStr, FormInt, FormFloat, 
                    FormBool, FormMenu, short_strings, ICON, STAGE_NAME)
from .modal_widgets import DateTimeDialog

lg = getLogger(__name__)

MAX_FREQUENCY_OF_INTEREST = 50

STAGE_SHORTCUT = ['1', '2', '3', '5', '9', '8', '0', '', '', '7']
QUALIFIERS = ['Good', 'Poor']
QUALITY_SHORTCUT = ['o', 'p']
SPINDLE_METHODS = ['Moelle2011',
                   'Ray2015',
                   'Wamsley2012',  
                   'Nir2011', 
                   'Ferrarelli2007',
                   'FASST',
                   'FASST2',
                   'UCSD', 
                   'Concordia',
                   ]
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
        self.index['min_marker_display_dur'] = FormFloat()
        self.index['min_marker_dur'] = FormFloat()

        flayout = QFormLayout()
        flayout.addRow(self.index['marker_show'])
        flayout.addRow('Color of markers in the dataset',
                           self.index['marker_color'])
        flayout.addRow(self.index['annot_show'])
        flayout.addRow('Color of bookmarks in annotations',
                           self.index['annot_bookmark_color'])
        flayout.addRow('Event markers appear at least this long on trace',
                       self.index['min_marker_display_dur'])
        flayout.addRow('Below this duration, markers and events have no '
                           'duration', self.index['min_marker_dur'])

        box0.setLayout(flayout)

        box1 = QGroupBox('Events')

        flayout = QFormLayout()
        box1.setLayout(flayout)

        box2 = QGroupBox('Stages')

        self.index['scoring_window'] = FormInt()

        flayout = QFormLayout()
        flayout.addRow('Default scoring epoch length',
                           self.index['scoring_window'])
        box2.setLayout(flayout)

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

        self.annot = None

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
        tab_annot.cellDoubleClicked.connect(self.reset_current_row)

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

        act = QAction('New name', self)
        act.triggered.connect(self.markers_to_events)
        actions['m2e_newname'] = act
        
        act = QAction('Keep marker names', self)
        act.triggered.connect(partial(self.markers_to_events, True))
        actions['m2e_keepname'] = act
        
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
        act.setShortcut('Ctrl+[')
        act.triggered.connect(self.get_cycle_mrkr)
        actions['cyc_start'] = act

        act = QAction('Set cycle end', self)
        act.setShortcut('Ctrl+]')
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

        act = QAction('Domino', self)
        act.triggered.connect(partial(self.import_staging, 'domino', 
                                      as_qual=True))
        actions['import_domino_qual'] = act

        act = QAction('Alice', self)
        act.triggered.connect(partial(self.import_staging, 'alice', 
                                      as_qual=True))
        actions['import_alice_qual'] = act

        act = QAction('Sandman', self)
        act.triggered.connect(partial(self.import_staging, 'sandman', 
                                      as_qual=True))
        actions['import_sandman_qual'] = act

        act = QAction('RemLogic', self)
        act.triggered.connect(partial(self.import_staging, 'remlogic', 
                                      as_qual=True))
        actions['import_remlogic_qual'] = act

        act = QAction('Compumedics', self)
        act.triggered.connect(partial(self.import_staging, 'compumedics', 
                                      as_qual=True))
        actions['import_compumedics_qual'] = act
        
        act = QAction('Import events', self)
        act.triggered.connect(self.import_events)
        actions['imp_evt_csv'] = act

        act = QAction('Export staging', self)
        act.triggered.connect(self.export)
        actions['export'] = act

        act = QAction('Export events...', self)
        act.triggered.connect(self.parent.show_export_events_dialog)
        actions['export_events'] = act

        act = QAction('Spindle...', self)
        act.triggered.connect(self.parent.show_spindle_dialog)
        act.setShortcut('Ctrl+Shift+s')
        act.setEnabled(False)
        actions['spindle'] = act

        act = QAction('Slow wave...', self)
        act.triggered.connect(self.parent.show_slow_wave_dialog)
        act.setShortcut('Ctrl+Shift+w')
        act.setEnabled(False)
        actions['slow_wave'] = act

        act = QAction('Analysis console', self)
        act.triggered.connect(self.parent.show_analysis_dialog)
        act.setShortcut('Ctrl+Shift+a')
        act.setEnabled(False)
        actions['analyze'] = act

        act = QAction('Sleep statistics', self)
        act.triggered.connect(self.export_sleeps_stats)
        actions['export_sleepstats'] = act

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

        self.enable_events()

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

    def enable_events(self):
        """enable slow wave and spindle detection if both
        annotations and channels are active.
        """
        if self.annot is not None and self.parent.channels.groups:
            self.action['merge_events'].setEnabled(True)
            self.action['spindle'].setEnabled(True)
            self.action['slow_wave'].setEnabled(True)
            self.action['analyze'].setEnabled(True)
        else:
            self.action['merge_events'].setEnabled(False)
            self.action['spindle'].setEnabled(False)
            self.action['slow_wave'].setEnabled(False)
            self.action['analyze'].setEnabled(False)

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
            self.epoch_length = self.annot.epoch_length

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
            lg.debug(msg)
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error adding bookmark')
            error_dialog.showMessage(msg)
            error_dialog.exec()
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
        marker_end = [mrk['end'] for mrk in markers]
        self.idx_marker.setProperty('start', marker_start)
        self.idx_marker.setProperty('end', marker_end)

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
        
        self.check_all_eventtype = check_all = QCheckBox('All event types')
        check_all.setCheckState(Qt.Checked)
        check_all.clicked.connect(self.toggle_eventtype)
        layout.addWidget(check_all)

        self.idx_eventtype_list = []
        for one_eventtype in event_types:
            self.idx_eventtype.addItem(one_eventtype)
            item = QCheckBox(one_eventtype)
            layout.addWidget(item)
            item.setCheckState(Qt.Checked)
            item.stateChanged.connect(self.update_annotations)
            item.stateChanged.connect(self.toggle_check_all_eventtype)
            self.idx_eventtype_list.append(item)

        self.idx_eventtype_scroll.setWidget(evttype_group)

    def toggle_eventtype(self):
        """Check or uncheck all event types in event type scroll.""" 
        check = self.check_all_eventtype.isChecked()
        
        for btn in self.idx_eventtype_list:
            btn.setChecked(check)
            
    def toggle_check_all_eventtype(self):
        """Check 'All' if all event types are checked in event type scroll."""
        checklist = asarray([btn.isChecked for btn in self.idx_eventtype_list])
        
        if not checklist.all():
            self.check_all_eventtype.setChecked(False)
    
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
        annot_name = [ann['name'] for ann in all_annot]
        self.idx_annot_list.setProperty('start', annot_start)
        self.idx_annot_list.setProperty('end', annot_end)
        self.idx_annot_list.setProperty('name', annot_name)

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
                highlight = self.parent.traces.highlight
                if highlight:
                    self.parent.traces.scene.removeItem(highlight)
                    highlight = None
                    self.parent.traces.event_sel = None

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
            marker_end_time = self.idx_marker.property('end')[row]
        else:
            marker_time = self.idx_annot_list.property('start')[row]
            marker_end_time = self.idx_annot_list.property('end')[row]

        window_length = self.parent.value('window_length')
        
        if self.parent.traces.action['centre_event'].isChecked():
            window_start = (marker_time + marker_end_time - window_length) / 2
        else:
            window_start = floor(marker_time / window_length) * window_length
            
        self.parent.overview.update_position(window_start)
        
        if table_type == 'annot':
            for annot in self.parent.traces.idx_annot:
                if annot.marker.x() == marker_time:
                    self.parent.traces.highlight_event(annot)
                    break

    def find_row(self, ev_start, ev_end):
        """Highlight event row in table from start and end time.
        
        Parameters
        ----------
        ev_start : float
            start time, in seconds from record start
        ev_end : float
            end time, in seconds from record start
            
        Returns
        -------
        int
            index of event row in idx_annot_list QTableWidget
        """
        all_starts = self.idx_annot_list.property('start')
        all_ends = self.idx_annot_list.property('end')
        
        for i, (start, end) in enumerate(zip(all_starts, all_ends)):
            if start == ev_start and end == ev_end:
                return i
        
        for i, start in enumerate(all_starts):
            if start == ev_start:
                return i
            
        for i, end in enumerate(all_ends):
            if end == ev_end:
                return i
        
        raise ValueError
        
    def get_sleepstage(self, stage_idx=None):
        """Score the sleep stage, using shortcuts or combobox."""
        if self.annot is None:  # remove if buttons are disabled
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error getting sleep stage')
            error_dialog.showMessage('No score file loaded')
            error_dialog.exec()
            return

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')

        if window_length != self.epoch_length:
            msg = ('Zoom to ' + str(self.epoch_length) + ' (epoch length) ' +
                   'for sleep scoring.')
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error getting sleep stage')
            error_dialog.showMessage(msg)
            error_dialog.exec()
            lg.debug(msg)
            return

        try:
            self.annot.set_stage_for_epoch(window_start,
                                           STAGE_NAME[stage_idx])

        except KeyError:
            msg = ('The start of the window does not correspond to any epoch ' +
                   'in sleep scoring file.\n\n'
                   'Switch to the appropriate window length in View, then use '
                   'Navigation --> Line Up with Epoch to line up the window.')
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error getting sleep stage')
            error_dialog.showMessage(msg)
            error_dialog.exec()
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
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error getting quality')
            error_dialog.showMessage(msg)
            error_dialog.exec()
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
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error getting quality')
            error_dialog.showMessage(msg)
            error_dialog.exec()
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
            msg = ('The start of the window does not correspond to any epoch '
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
            msg = ('The start of the window does not correspond to any cycle '
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
        #lg.info('winstart: ' + str(window_start) + ', stage: ' + str(stage))

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
        #lg.info('winstart: ' + str(window_start) + ', quality: ' + str(qual))

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

    def import_staging(self, source, staging_start=None, as_qual=False,
                       test_filename=None, test_rater=None):
        """Action: import an external sleep staging file.

        Parameters
        ----------
        source : str
            Name of program where staging was exported. One of 'alice',
            'compumedics', 'domino', 'remlogic', 'sandman'.
        staging_start : datetime, optional
            Absolute time when staging begins.
        as_qual : bool
            if True, scores will be imported as quality
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

            if rater in self.annot.raters and not as_qual:
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

        poor = ['Artefact', 'Artifact']
        if as_qual:
            query = 'Which epoch label should be read as Poor quality signal?'
            poor, ok = QInputDialog.getText(self, 'Import quality', query)
            poor = [poor]
            
            if not ok:
                return
        
        try:
            unaligned = self.annot.import_staging(filename, source, rater,
                                                  record_start,
                                                  staging_start=staging_start,
                                                  poor=poor, 
                                                  as_qual=as_qual)
        except FileNotFoundError:
            msg = 'File not found'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)
            
        if unaligned:
            msg = 'Imported scores are not aligned with existing scores.'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)

        self.display_notes()
        self.parent.create_menubar()  # refresh list ot raters

    def new_rater(self):
        """Action: add a new rater.
        """
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        newuser = NewUserDialog(self.parent.value('scoring_window'))
        answer = newuser.exec_()

        if answer == QDialog.Rejected:
            return

        rater_name = newuser.rater_name.text()

        if rater_name != '':
            self.annot.add_rater(rater_name, newuser.epoch_length.value())
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
            
        return answer

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

    def markers_to_events(self, keep_name=False):
        """Copy all markers in dataset to event type. """
        markers = self.parent.info.markers
        
        if markers is None:
            self.parent.statusBar.showMessage('No markers in dataset.')
            return
        
        if not keep_name:
            name, ok = self.new_eventtype()
            
            if not ok:
                return

        progress = QProgressDialog('Saving events', 'Abort',
                                       0, len(markers), self)
        progress.setWindowModality(Qt.ApplicationModal)
        
        for i, mrk in enumerate(markers):
            progress.setValue(i)
            
            if keep_name:
                name = mrk['name']
                
            self.annot.add_event(name, (mrk['start'], mrk['end']), chan='')
            
            if progress.wasCanceled():
                msg = ('Conversion interrupted. Not all events were saved '
                       'to the Annotations File.')
                self.parent.statusBar().showMessage(msg)
                return
            
        progress.setValue(i + 1)
        
        if keep_name:
            self.display_eventtype()
            n_eventtype = self.idx_eventtype.count()
            self.idx_eventtype.setCurrentIndex(n_eventtype - 1)
        
        self.update_annotations()
    
    def detect_events(self, data, method, params, label):
        """Detect events and display on signal.

        Parameters
        ----------
        data : instance of ChanTime
            one segment with all channels of interest
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

        if params['max_dur'] in [0, 'None']:
            params['max_dur'] = None

        freq = (float(params['f1']), float(params['f2']))
        duration = (params['min_dur'], params['max_dur'])

        if method in SPINDLE_METHODS:
            detector = DetectSpindle(method=method, frequency=freq,
                                     duration=duration, merge=params['merge'])

            if method in ['Wamsley2012', 'UCSD']:
                detector.det_wavelet['dur'] = params['win_sz']
            elif method == 'Ray2015':
                detector.zwin['dur'] = params['win_sz']
            else:
                detector.moving_rms['dur'] = params['win_sz']

            detector.det_wavelet['sd'] = params['sigma']
            detector.smooth['dur'] = params['smooth']
            detector.det_thresh_lo = params['det_thresh_lo']
            detector.det_thresh_hi = params['det_thresh_hi']
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

        events = detector(data, parent=self)

        if events:
            progress = QProgressDialog('Saving events', 'Abort',
                                       0, len(events), self)
            progress.setWindowModality(Qt.ApplicationModal)
    
            for i, one_ev in enumerate(events):
                progress.setValue(i)
                self.annot.add_event(label,(one_ev['start'],
                                            one_ev['end']),
                                            chan=one_ev['chan'])
                if progress.wasCanceled():
                    msg = ('Saving interrupted. Not all events were saved '
                           'to the Annotations File.')
                    self.parent.statusBar().showMessage(msg)
                    return
    
            progress.setValue(i + 1)

        self.update_annotations()

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

    def import_events(self):
        """action: import events from Wonambi CSV event export."""
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        fn, _ = QFileDialog.getOpenFileName(self, 'Import events',
                                            None, 'CSV File (*.csv)')
        
        if fn == '':
            return
        
        fn = Path(fn).resolve()

        self.annot.import_events(fn, parent=self.parent)
        self.display_notes()        
    
    def export_sleeps_stats(self):
        """action: export sleep statistics CSV."""
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        fn = splitext(self.annot.xml_file)[0] + '_sleepstats.csv'
        fn, _ = QFileDialog.getSaveFileName(self, 'Export sleep statistics',
                                            fn, 'Sleep stats (*.csv)')
        if fn == '':
            return

        dt_dialog = DateTimeDialog('Lights OUT', self.annot.start_time,
                                   self.annot.last_second)
        if not dt_dialog.exec():
            return
        lights_out = dt_dialog.idx_seconds.value()

        dt_dialog = DateTimeDialog('Lights ON', self.annot.start_time,
                                   self.annot.last_second)
        if not dt_dialog.exec():
            return
        lights_on = dt_dialog.idx_seconds.value()

        lights_out, lights_on = float(lights_out), float(lights_on)

        if self.annot.export_sleep_stats(fn, lights_out, lights_on) is None:
            self.parent.statusBar().showMessage('No epochs scored as sleep.')

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
        
    def reset_current_row(self):
        """For traces.next_event"""
        self.parent.traces.current_event_row = None


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
    idx_merge_to : FormMenu
        Choice of 'earlier onset event' or 'longer duration event'.
    merge_to : str
        Current text in idx_merge_to
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

        self.idx_merge_to = FormMenu(['earlier onset event', 
                                      'longer duration event'])
        self.merge_to = self.idx_merge_to.currentText()

        self.min_interval = FormFloat()
        self.cross_chan = FormBool('Merge across channels')

        self.min_interval.set_value(1.0)
        self.cross_chan.setCheckState(Qt.Checked)

        flayout = QFormLayout()
        box0.setLayout(flayout)
        flayout.addRow('Event type(s)',
                           self.idx_evt_type)
        flayout.addRow(self.cross_chan)
        flayout.addRow('Merge to...',
                           self.idx_merge_to)
        flayout.addRow('Min. interval (sec)',
                           self.min_interval)

        bbox = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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

            min_interval = 0 if not min_interval else min_interval

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

    def update_event_types(self):
        """Update event types in event type box."""
        self.idx_evt_type.clear()
        self.idx_evt_type.setSelectionMode(QAbstractItemView.ExtendedSelection)
        event_types = sorted(self.parent.notes.annot.event_types,
                             key=str.lower)

        for ty in event_types:
            item = QListWidgetItem(ty)
            self.idx_evt_type.addItem(item)


class NewUserDialog(QDialog):

    def __init__(self, default_length):
        super().__init__()
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)

        bbox.clicked.connect(self.button_clicked)

        self.rater_name = QLineEdit('')
        self.epoch_length = QSpinBox()
        self.epoch_length.setValue(default_length)

        f = QFormLayout()
        f.addRow('Rater\'s name', self.rater_name)
        f.addRow('Epoch Length', self.epoch_length)
        f.addRow(bbox)

        self.setLayout(f)
        self.show()

    def button_clicked(self, button):
        if button == self.idx_ok:
            self.accept()

        elif button == self.idx_cancel:
            self.reject()


class ExportEventsDialog(QDialog):
    """Dialog for choosing export dataset options."""
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent
        
        self.setWindowTitle('Export events')
        self.setWindowModality(Qt.WindowModal)
        self.filename = None

        self.create_dialog()

    def create_dialog(self):
        """Create the dialog."""
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)

        filebutton = QPushButton()
        filebutton.setText('Choose')
        self.idx_filename = filebutton
        
        self.xp_format = FormMenu(['CSV', 'Brain Vision'])
        self.all_types = FormBool('All event types')
        
        self.idx_evt_type = QListWidget()
        self.idx_evt_type.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        filebutton.clicked.connect(self.save_as)
        self.all_types.connect(self.toggle_buttons)
        bbox.clicked.connect(self.button_clicked)
        
        form = QFormLayout()
        form.addRow('Filename', self.idx_filename)
        form.addRow('Format', self.xp_format)
        form.addRow(self.all_types)
        form.addRow('Event type(s)', self.idx_evt_type)
        
        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addLayout(form)
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
            fn = Path(self.filename)
            xp_format = self.xp_format.get_value()
            
            if self.all_types.get_value():
                evt_type = self.event_types
            else:
                evt_type = [
                        x.text() for x in self.idx_evt_type.selectedItems()]
                
            if 'CSV' == xp_format:
                                
                self.parent.notes.annot.export_events(fn, evt_type)
            
            elif 'Brain Vision' == xp_format:
                
                events = []
                for et in evt_type:                
                    events.extend(self.parent.notes.annot.get_events(name=et))
        
                if not events:
                    self.parent.statusBar.showMessage('No events found.')
                    return
                
                dataset = self.parent.info.dataset
                data = ChanTime()
                data.start_time = dataset.header['start_time']
                data.s_freq = int(dataset.header['s_freq'])
                
                with fn.with_suffix('.vmrk').open('w') as f:
                    lg.info('Writing to ' + str(fn) + '.vmrk')
                    f.write(_write_vmrk(data, fn, events))
                
            self.accept()
            
        if button is self.idx_cancel:
            self.reject()
        
    def update(self):
        """Update the event types list, info, when dialog is opened."""
        self.filename = self.parent.notes.annot.xml_file
        
        self.event_types = self.parent.notes.annot.event_types
        self.idx_evt_type.clear()
        for ev in self.event_types:
            self.idx_evt_type.addItem(ev)
            
    def toggle_buttons(self):
        """Turn buttons on and off."""
        all_types = self.all_types.get_value()
        self.idx_evt_type.setEnabled(not all_types)
    
    def save_as(self):
        """Dialog for getting name, location of dataset export."""
        filename = splitext(self.filename)[0]
        filename, _ = QFileDialog.getSaveFileName(self, 'Export events',
                                                  filename)
        if filename == '':
            return

        self.filename = filename
        short_filename = short_strings(basename(self.filename))
        self.idx_filename.setText(short_filename)
