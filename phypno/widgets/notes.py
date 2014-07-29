"""Widgets containing notes (such as markers, events, and stages).

  - markers are unique (might have the same text), are not mutually
    exclusive, do not have duration
  - events are not unique, are not mutually exclusive, have variable duration
  - stages are not unique, are mutually exclusive, have fixed duration

"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta, datetime
from functools import partial
from math import floor
from os.path import basename, splitext

from PyQt4.QtGui import (QAbstractItemView,
                         QAction,
                         QColor,
                         QComboBox,
                         QFileDialog,
                         QFormLayout,
                         QGroupBox,
                         QHBoxLayout,
                         QIcon,
                         QInputDialog,
                         QLabel,
                         QListWidget,
                         QListWidgetItem,
                         QPushButton,
                         QTableWidget,
                         QTableWidgetItem,
                         QTabWidget,
                         QWidget,
                         QVBoxLayout,
                         )

from ..attr import Annotations, create_empty_annotations

from .settings import Config, FormStr, FormInt
from .utils import short_strings, ICON

# TODO: this in ConfigNotes
STAGE_NAME = ['Wake', 'Movement', 'REM', 'NREM1', 'NREM2', 'NREM3',
              'Undefined', 'Unknown']
STAGE_SHORTCUT = ['9', '8', '5', '1', '2', '3', '0', '']


class ConfigNotes(Config):

    def __init__(self, update_widget):
        super().__init__('notes', update_widget)

    def create_config(self):

        box0 = QGroupBox('Markers')

        self.index['dataset_marker_color'] = FormStr()
        self.index['annot_marker_color'] = FormStr()

        form_layout = QFormLayout()
        form_layout.addRow('Color of markers in the dataset',
                           self.index['dataset_marker_color'])
        form_layout.addRow('Color of markers in annotations',
                           self.index['annot_marker_color'])
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


    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.config = ConfigNotes(lambda: None)
        self.annot = None
        self.dataset_markers = None  # shouldn't this be in info?

        self.idx_annotations = None
        self.idx_rater = None
        self.idx_stats = None

        self.idx_marker = None
        self.idx_eventtype = None  # combobox of eventtype
        self.idx_eventtype_list = None  # list of event types
        self.idx_event_list = None  # list of events
        self.idx_stage = None

        self.create()
        self.create_action()

    def create(self):

        """ ------ ANNOTATIONS ------ """
        tab0 = QWidget()
        self.idx_eventtype = QComboBox(self)
        self.idx_stage = QComboBox(self)
        self.idx_stage.activated.connect(self.get_sleepstage)

        self.idx_annotations = QPushButton('Load Annotation File...')
        self.idx_annotations.clicked.connect(self.load_annot)
        self.idx_rater = QLabel('')

        self.idx_stats = QFormLayout()

        b0 = QGroupBox('Info')
        form = QFormLayout()
        b0.setLayout(form)

        form.addRow('File:', self.idx_annotations)
        form.addRow('Rater:', self.idx_rater)

        b1 = QGroupBox('Recap')
        b1.setLayout(self.idx_stats)

        layout = QVBoxLayout()
        layout.addWidget(b0)
        layout.addWidget(b1)

        tab0.setLayout(layout)

        """ ------ MARKERS ------ """
        tab1 = QTableWidget()
        self.idx_marker = tab1

        tab1.setColumnCount(2)
        tab1.setHorizontalHeaderLabels(['Time', 'Text'])
        tab1.horizontalHeader().setStretchLastSection(True)
        tab1.setSelectionBehavior(QAbstractItemView.SelectRows)
        tab1.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tab1.cellDoubleClicked.connect(self.go_to_marker)

        """ ------ EVENTS ------ """
        tab2 = QWidget()
        self.idx_eventtype_list = QListWidget()
        self.idx_eventtype_list.itemSelectionChanged.connect(self.display_events)
        tab_events = QTableWidget()
        self.idx_event_list = tab_events

        tab_events.setColumnCount(2)
        tab_events.setHorizontalHeaderLabels(['Time', 'Event Type'])
        tab_events.horizontalHeader().setStretchLastSection(True)
        tab_events.setSelectionBehavior(QAbstractItemView.SelectRows)
        tab_events.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # tab_events.cellDoubleClicked.connect(self.go_to_marker)

        layout = QHBoxLayout()
        layout.addWidget(self.idx_eventtype_list)
        layout.addWidget(self.idx_event_list)
        tab2.setLayout(layout)

        """ ------ TABS ------ """
        self.addTab(tab0, 'Annotations')
        self.addTab(tab1, 'Markers')
        self.addTab(tab2, 'Events')

    def create_action(self):
        output = {}

        act = QAction('New Annotation File...', self)
        act.triggered.connect(self.new_annot)
        output['new_annot'] = act

        act = QAction('Load Annotation File...', self)
        act.triggered.connect(self.load_annot)
        output['load_annot'] = act

        act = QAction('New...', self)
        act.triggered.connect(self.new_rater)
        output['new_rater'] = act

        act = QAction('Delete...', self)
        act.triggered.connect(self.delete_rater)
        output['del_rater'] = act

        act = QAction(QIcon(ICON['marker']), 'New Marker', self)
        act.setCheckable(True)
        output['new_marker'] = act

        act = QAction(QIcon(ICON['new_eventtype']), 'New Event Type', self)
        act.triggered.connect(self.new_eventtype)
        output['new_eventtype'] = act

        act = QAction(QIcon(ICON['del_eventtype']), 'Delete Event Type', self)
        act.triggered.connect(self.delete_eventtype)
        output['del_eventtype'] = act

        act = QAction(QIcon(ICON['event']), 'New Event', self)
        act.setCheckable(True)
        output['new_event'] = act

        uncheck_new_event = lambda: output['new_event'].setChecked(False)
        uncheck_new_marker = lambda: output['new_marker'].setChecked(False)
        output['new_event'].triggered.connect(uncheck_new_marker)
        output['new_marker'].triggered.connect(uncheck_new_event)

        act = {}
        for one_stage, one_shortcut in zip(STAGE_NAME, STAGE_SHORTCUT):
            act[one_stage] = QAction('Score as ' + one_stage, self.parent)
            act[one_stage].setShortcut(one_shortcut)
            stage_idx = STAGE_NAME.index(one_stage)
            act[one_stage].triggered.connect(partial(self.get_sleepstage,
                                                     stage_idx))
            self.addAction(act[one_stage])

        output['stages'] = act

        self.action = output

    def update_notes(self, xml_file, new=False):
        """Update information about the sleep scoring.

        Parameters
        ----------
        xml_file : str
            file of the new or existing .xml file

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

        for one_stage in STAGE_NAME:
            self.idx_stats.addRow(one_stage, QLabel(''))

        self.display_notes()

    def update_dataset_markers(self, header):
        """called by info.open_dataset

        TODO: specific to Ktlx, check for all the markers/triggers."""
        markers = []
        splitted = header['orig']['notes'].split('\n')
        for mrk in splitted:
            values = mrk.split(',')
            mrk_time = datetime.strptime(values[0], '%Y-%m-%dT%H:%M:%S')
            mrk_sec = (mrk_time - header['start_time']).total_seconds()

            markers.append({'time': mrk_sec,
                            'name': ','.join(values[2:])
                            })
        self.dataset_markers = markers
        self.display_markers()

    def display_notes(self):
        """Display information about scores and raters.

        This function is called by overview.display and it ends up
        calling the functions in overview. But conceptually it belongs here.

        """
        short_xml_file = short_strings(basename(self.annot.xml_file))
        self.idx_annotations.setText(short_xml_file)
        try:
            # if annotations were loaded without dataset
            if self.parent.overview.scene is None:
                self.parent.overview.update()

            self.idx_rater.setText(self.annot.current_rater)

            self.display_markers()
            self.display_eventtype()

            for epoch in self.annot.epochs:
                self.parent.overview.display_stages(epoch['start'],
                                                    epoch['end'] -
                                                    epoch['start'],
                                                    epoch['stage'])

            self.display_stats()

        except IndexError:
            self.idx_rater.setText('')

    def display_stats(self):
        """Display summary statistics about duration in each stage."""
        for i, one_stage in enumerate(STAGE_NAME):
            second_in_stage = self.annot.time_in_stage(one_stage)
            time_in_stage = str(timedelta(seconds=second_in_stage))

            label = self.idx_stats.itemAt(i, QFormLayout.FieldRole).widget()
            label.setText(time_in_stage)

    def add_marker(self, time):

        answer = QInputDialog.getText(self, 'New Marker',
                                      'Enter marker\'s name')
        if answer[1]:
            name = answer[0]
            self.annot.add_marker(name, time)
            lg.info('Added Marker ' + name + 'at ' + str(time))

        self.display_markers()

    def display_markers(self):

        start_time = self.parent.overview.start_time

        annot_markers = []
        if self.parent.notes.annot is not None:
            annot_markers = self.parent.notes.annot.get_markers()

        dataset_markers = []
        if self.parent.notes.dataset_markers is not None:
            dataset_markers = self.parent.notes.dataset_markers

        markers = annot_markers + dataset_markers
        markers = sorted(markers, key=lambda x: x['time'])

        self.idx_marker.clear()
        self.idx_marker.setRowCount(len(markers))

        for i, mrk in enumerate(markers):
            abs_time = (start_time +
                        timedelta(seconds=mrk['time'])).strftime('%H:%M:%S')
            item_time = QTableWidgetItem(abs_time)
            self.idx_marker.setItem(i, 0, item_time)

            item_name = QTableWidgetItem(mrk['name'])
            self.idx_marker.setItem(i, 1, item_name)

            if mrk in annot_markers:
                color = self.parent.value('annot_marker_color')
            if mrk in dataset_markers:
                color = self.parent.value('dataset_marker_color')
            item_time.setTextColor(QColor(color))
            item_name.setTextColor(QColor(color))

        # store information about the time as list (easy to access)
        marker_time = [mrk['time'] for mrk in markers]
        self.idx_marker.setProperty('time', marker_time)

        if self.parent.traces.data is not None:
            self.parent.traces.display()  # redo the whole figure
        self.parent.overview.display_markers()

    def go_to_marker(self, row, col):
        """Move to point in time marked by the marker.

        Parameters
        ----------
        row : QtCore.int

        column : QtCore.int

        """
        window_length = self.parent.value('window_length')
        marker_time = self.idx_marker.property('time')[row]
        window_start = floor(marker_time / window_length) * window_length
        self.parent.overview.update_position(window_start)

    def get_sleepstage(self, stage_idx=None):
        """Get the sleep stage, using shortcuts or combobox.

        Parameters
        ----------
        stage : str
            string with the name of the sleep stage.

        """
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
            self.parent.overview.display_stages(window_start, window_length,
                                                STAGE_NAME[stage_idx])
            self.display_stats()
            self.parent.action_page_next()

    def set_stage_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.value('window_start')
        stage = self.annot.get_stage_for_epoch(window_start)
        if stage is None:
            self.idx_stage.setCurrentIndex(-1)
        else:
            self.idx_stage.setCurrentIndex(STAGE_NAME.index(stage))

    def new_annot(self):
        """Action: create a new file for annotations.

        It should be gray-ed out when no dataset
        """
        if self.parent.info.filename is None:
            self.parent.statusBar().showMessage('No dataset loaded')
            return

        filename = splitext(self.parent.info.filename)[0] + '_scores.xml'
        filename = QFileDialog.getSaveFileName(self, 'Create annotation file',
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
            filename = '/home/gio/tools/phypno/data/MGXX/doc/scores/MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml'  # TODO

        filename = QFileDialog.getOpenFileName(self, 'Load annotation file',
                                               filename,
                                               'Annotation File (*.xml)')

        if filename == '':
            return

        try:
            self.update_notes(filename, False)
        except FileNotFoundError:
            self.parent.statusBar().showMessage('Annotation file not found')

    def new_rater(self):
        """
        First argument, if not specified, is a bool/False:
        http://pyqt.sourceforge.net/Docs/PyQt4/qaction.html#triggered

        """
        answer = QInputDialog.getText(self, 'New Rater',
                                      'Enter rater\'s name')
        if answer[1]:
            self.annot.add_rater(answer[0])
            self.display_notes()
            self.parent.create_menubar()  # refresh list ot raters

    def select_rater(self, rater=False):
        self.annot.get_rater(rater)
        self.display_notes()

    def delete_rater(self):
        answer = QInputDialog.getText(self, 'Delete Rater',
                                      'Enter rater\'s name')
        if answer[1]:
            self.annot.remove_rater(answer[0])
            self.display_notes()
            self.parent.create_menubar()  # refresh list ot raters

    def new_eventtype(self):
        answer = QInputDialog.getText(self, 'New Event Type',
                                      'Enter new event\'s name')
        if answer[1]:
            self.annot.add_event_type(answer[0])
            self.display_eventtype()
            n_eventtype = self.idx_eventtype.count()
            self.idx_eventtype.setCurrentIndex(n_eventtype - 1)

    def delete_eventtype(self):
        answer = QInputDialog.getText(self, 'Delete Event Type',
                                      'Enter event\'s name to delete')
        if answer[1]:
            self.annot.remove_event_type(answer[0])
            self.display_eventtype()

    def display_eventtype(self):
        self.idx_eventtype.clear()
        self.idx_eventtype_list.clear()
        ExtendedSelection = QAbstractItemView.SelectionMode(3)
        self.idx_eventtype_list.setSelectionMode(ExtendedSelection)

        for one_eventytype in self.annot.event_types:
            self.idx_eventtype.addItem(one_eventytype)
            item = QListWidgetItem(one_eventytype)
            self.idx_eventtype_list.addItem(item)
            item.setSelected(True)

        self.display_events()

    def add_event(self, name, time):
        self.annot.add_event(name, time)
        self.display_events()

    def display_events(self):
        self.idx_event_list.clearContents()

        selectedItems = self.idx_eventtype_list.selectedItems()

        eventtypes = (x.text() for x in selectedItems)
        events = []
        for one_eventtype in eventtypes:
            evts = self.annot.get_events(one_eventtype)
            events.extend(evts)

        start_time = self.parent.overview.start_time

        events = sorted(events, key=lambda x: x['start'])
        self.idx_event_list.setRowCount(len(events))

        for i, evt in enumerate(events):
            start = (start_time +
                     timedelta(seconds=evt['start'])).strftime('%H:%M:%S')
            end = (start_time +
                   timedelta(seconds=evt['end'])).strftime('%H:%M:%S')
            abs_time = start + '-' + end
            # chan_name = ', '.join(evt['chan'])
            self.idx_event_list.setItem(i, 0, QTableWidgetItem(abs_time))
            self.idx_event_list.setItem(i, 1, QTableWidgetItem(evt['name']))

        self.parent.overview.display_events()
        self.parent.traces.display()

    def reset(self):
        self.idx_annotations.setText('Load Annotation File...')
        self.idx_rater.setText('')
        self.idx_stats = QFormLayout()

        self.idx_marker.clear()

        self.idx_eventtype.clear()
        self.idx_eventtype_list.clear()
        self.idx_event_list.clear()

        self.annot = None
        self.dataset_markers = None
