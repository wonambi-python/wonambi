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
from datetime import timedelta
from functools import partial
from logging import getLogger
from math import floor
from os.path import basename, splitext

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (QAbstractItemView,
                             QAction,
                             QCheckBox,
                             QComboBox,
                             QFileDialog,
                             QFormLayout,
                             QGroupBox,
                             QInputDialog,
                             QLabel,
                             QMessageBox,
                             QPushButton,
                             QTableWidget,
                             QTableWidgetItem,
                             QTabWidget,
                             QVBoxLayout,
                             QWidget,
                             QScrollArea,
                             )

from ..attr import Annotations, create_empty_annotations
from .settings import Config, FormStr, FormInt, FormFloat, FormBool
from .utils import convert_name_to_color, short_strings, ICON

lg = getLogger(__name__)

# TODO: this in ConfigNotes
STAGE_NAME = ['Wake', 'Movement', 'REM', 'NREM1', 'NREM2', 'NREM3',
              'Undefined', 'Unknown']
STAGE_SHORTCUT = ['9', '8', '5', '1', '2', '3', '0', '']


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

        self.idx_annotations = QPushButton('Load Annotation File...')
        self.idx_annotations.clicked.connect(self.load_annot)
        self.idx_rater = QLabel('')

        b0 = QGroupBox('Info')
        form = QFormLayout()
        b0.setLayout(form)

        form.addRow('File:', self.idx_annotations)
        form.addRow('Rater:', self.idx_rater)

        b1 = QGroupBox('Recap')

        layout = QVBoxLayout()
        layout.addWidget(b0)
        layout.addWidget(b1)
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

        tab_annot.setColumnCount(4)
        tab_annot.setHorizontalHeaderLabels(['Start', 'Duration', 'Text',
                                             'Type'])
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

        act = QAction('New Annotation File...', self)
        act.triggered.connect(self.new_annot)
        actions['new_annot'] = act

        act = QAction('Load Annotation File...', self)
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

        act = QAction(QIcon(ICON['event']), 'New Event', self)
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

        act = QAction('Export...', self)
        act.triggered.connect(self.export)
        actions['export'] = act

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

        self.parent.create_menubar()
        self.idx_stage.clear()
        for one_stage in STAGE_NAME:
            self.idx_stage.addItem(one_stage)
        self.idx_stage.setCurrentIndex(-1)

        w = self.idx_summary.takeAt(1).widget()
        self.idx_summary.removeWidget(w)
        w.deleteLater()

        b1 = QGroupBox('Recap')

        layout = QFormLayout()
        for one_stage in STAGE_NAME:
            layout.addRow(one_stage, QLabel(''))
        b1.setLayout(layout)
        self.idx_summary.addWidget(b1)
        self.idx_stats = layout

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

            label = self.idx_stats.itemAt(i, QFormLayout.FieldRole).widget()
            label.setText(time_in_stage)

    def add_bookmark(self, time):
        """Run this function when user adds a new bookmark.

        Parameters
        ----------
        time : tuple of float
            start and end of the new bookmark, in s
        """
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
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
        lg.info('lenght annotations ' + str(len(all_annot)))

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

            item_time.setForeground(QColor(color))
            item_duration.setForeground(QColor(color))
            item_name.setForeground(QColor(color))
            item_type.setForeground(QColor(color))

            self.idx_annot_list.setItem(i, 0, item_time)
            self.idx_annot_list.setItem(i, 1, item_duration)
            self.idx_annot_list.setItem(i, 2, item_name)
            self.idx_annot_list.setItem(i, 3, item_type)

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
        """Get the sleep stage, using shortcuts or combobox.

        Parameters
        ----------
        stage : str
            string with the name of the sleep stage.
        """
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')

        try:
            self.annot.set_stage_for_epoch(window_start,
                                           STAGE_NAME[stage_idx])

        except KeyError:
            self.parent.statusBar().showMessage('The start of the window does '
                                                'not correspond to any epoch '
                                                'in sleep scoring file')

        else:
            lg.info('User staged ' + str(window_start) + ' as ' +
                    STAGE_NAME[stage_idx])

            self.set_stage_index()
            self.parent.overview.mark_stages(window_start, window_length,
                                             STAGE_NAME[stage_idx])
            self.display_stats()
            self.parent.traces.page_next()

    def set_stage_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.value('window_start')
        stage = self.annot.get_stage_for_epoch(window_start)
        if stage is None:
            self.idx_stage.setCurrentIndex(-1)
        else:
            self.idx_stage.setCurrentIndex(STAGE_NAME.index(stage))

    def new_annot(self):
        """Action: create a new file for annotations."""
        if self.parent.info.filename is None:
            self.parent.statusBar().showMessage('No dataset loaded')
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
            self.parent.statusBar().showMessage('Annotation file not found')

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

    def delete_rater(self):
        """Action: create dialog to delete rater."""
        answer = QInputDialog.getText(self, 'Delete Rater',
                                      'Enter rater\'s name')
        if answer[1]:
            self.annot.remove_rater(answer[0])
            self.display_notes()
            self.parent.create_menubar()  # refresh list ot raters

    def new_eventtype(self):
        """Action: create dialog to add new event type."""
        if self.annot is None:  # remove if buttons are disabled
            self.parent.statusBar().showMessage('No score file loaded')
            return

        answer = QInputDialog.getText(self, 'New Event Type',
                                      'Enter new event\'s name')
        if answer[1]:
            self.annot.add_event_type(answer[0])
            self.display_eventtype()
            n_eventtype = self.idx_eventtype.count()
            self.idx_eventtype.setCurrentIndex(n_eventtype - 1)

    def delete_eventtype(self):
        """Action: create dialog to delete event type."""
        answer = QInputDialog.getText(self, 'Delete Event Type',
                                      'Enter event\'s name to delete')
        if answer[1]:
            self.annot.remove_event_type(answer[0])
            self.display_eventtype()

    def add_event(self, name, time):
        """Action: add a single event."""
        self.annot.add_event(name, time)
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
        w = self.idx_summary.takeAt(1).widget()
        self.idx_summary.removeWidget(w)
        w.deleteLater()
        b1 = QGroupBox('Recap')
        self.idx_summary.addWidget(b1)

        # remove annotations
        self.display_eventtype()
        self.update_annotations()

        self.parent.create_menubar()  # remove all raters
