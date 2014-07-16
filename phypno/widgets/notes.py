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
from os.path import basename

from PyQt4.QtGui import (QAbstractItemView,
                         QAction,
                         QComboBox,
                         QFormLayout,
                         QGroupBox,
                         QHBoxLayout,
                         QInputDialog,
                         QLabel,
                         QListWidget,
                         QPushButton,
                         QTableView,
                         QTableWidget,
                         QTableWidgetItem,
                         QTabWidget,
                         QWidget,
                         QVBoxLayout,
                         )

from ..attr import Annotations, create_empty_annotations

from .settings import Config, FormInt
from .utils import short_strings

# TODO: this in ConfigNotes
STAGE_NAME = ['Wake', 'Movement', 'REM', 'NREM1', 'NREM2', 'NREM3', 'Unknown']
STAGE_SHORTCUT = ['9', '8', '5', '1', '2', '3', '0']


class ConfigNotes(Config):

    def __init__(self, update_widget):
        super().__init__('stages', update_widget)

    def create_config(self):

        box0 = QGroupBox('Stages')

        self.index['scoring_window'] = FormInt()

        form_layout = QFormLayout()
        form_layout.addRow('Length of scoring window',
                           self.index['scoring_window'])
        box0.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
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
        self.dataset_markers = None

        self.idx_annotations = None
        self.idx_rater = None
        self.idx_stats = None

        self.idx_marker = None
        self.idx_event = None
        self.idx_event_list = None
        self.idx_stage = None

        self.create_notes()
        self.create_staging_actions()

    def create_notes(self):

        """ ------ ANNOTATIONS ------ """
        tab0 = QWidget()
        self.idx_eventtype = QComboBox(self)
        self.idx_stage = QComboBox(self)
        self.idx_stage.activated.connect(self.get_sleepstage)

        self.idx_annotations = QPushButton('Load Annotation File...')
        self.idx_annotations.clicked.connect(self.parent.action_load_annot)
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
        self.idx_events = QListWidget()
        self.idx_event_list = QTableView()

        layout = QHBoxLayout()
        layout.addWidget(self.idx_events)
        layout.addWidget(self.idx_event_list)
        tab2.setLayout(layout)

        """ ------ TABS ------ """
        self.addTab(tab0, 'Annotations')
        self.addTab(tab1, 'Markers')
        self.addTab(tab2, 'Events')

    def create_staging_actions(self):
        """Create actions and shortcut to score sleep."""
        actions = {}
        for one_stage, one_shortcut in zip(STAGE_NAME, STAGE_SHORTCUT):
            actions[one_stage] = QAction('Score as ' + one_stage, self.parent)
            actions[one_stage].setShortcut(one_shortcut)
            stage_idx = STAGE_NAME.index(one_stage)
            actions[one_stage].triggered.connect(partial(self.get_sleepstage,
                                                         stage_idx))
            self.addAction(actions[one_stage])
        self.action = actions

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
        """TODO: specific to Ktlx, check for all the markers/triggers."""
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
        self.mark_markers()

    def display_notes(self):
        """Display information about scores and raters.

        This function is called by overview.display_overview and it ends up
        calling the functions in overview. But conceptually it belongs here.

        """
        short_xml_file = short_strings(basename(self.annot.xml_file))
        self.idx_annotations.setText(short_xml_file)
        try:
            # if annotations were loaded without dataset
            if self.parent.overview.scene is None:
                self.parent.overview.update_overview()

            self.idx_rater.setText(self.annot.current_rater)

            self.mark_markers()

            for epoch in self.annot.epochs:
                self.parent.overview.mark_stages(epoch['start'],
                                                 epoch['end'] -
                                                 epoch['start'],
                                                 epoch['stage'])

            self.display_recap()

        except IndexError:
            self.idx_rater.setText('')

    def display_recap(self):
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

        self.mark_markers()

    def mark_markers(self):

        start_time = self.parent.overview.start_time

        markers = []
        if self.annot is not None:
            # color
            markers.extend(self.annot.get_markers())
        if self.dataset_markers is not None:
            markers.extend(self.dataset_markers)

        self.idx_marker.clear()  # TODO: keep selection?

        markers = sorted(markers, key=lambda x: x['time'])
        self.idx_marker.setRowCount(len(markers))
        for i, mrk in enumerate(markers):
            abs_time = (start_time +
                        timedelta(seconds=mrk['time'])).strftime('%H:%M:%S')
            self.idx_marker.setItem(i, 0, QTableWidgetItem(abs_time))
            self.idx_marker.setItem(i, 1, QTableWidgetItem(mrk['name']))

        self.parent.traces.mark_markers()
        self.parent.overview.mark_markers()

    def go_to_marker(self, row, col):
        """Move to point in time marked by the marker.

        Parameters
        ----------
        row : QtCore.int

        column : QtCore.int

        """
        window_length = self.parent.overview.config.value['window_length']
        marker_time = self.dataset_markers[row]['time']
        window_start = floor(marker_time / window_length) * window_length
        self.parent.overview.update_position(window_start)

    def get_sleepstage(self, stage_idx=None):
        """Get the sleep stage, using shortcuts or combobox.

        Parameters
        ----------
        stage : str
            string with the name of the sleep stage.

        """
        window_start = self.parent.overview.config.value['window_start']
        window_length = self.parent.overview.config.value['window_length']

        lg.info('User staged ' + str(window_start) + ' as ' +
                STAGE_NAME[stage_idx])
        self.annot.set_stage_for_epoch(window_start, STAGE_NAME[stage_idx])
        self.set_combobox_index()
        self.parent.overview.mark_stages(window_start, window_length,
                                         STAGE_NAME[stage_idx])
        self.display_recap()
        self.parent.action_page_next()

    def set_combobox_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.overview.config.value['window_start']
        stage = self.annot.get_stage_for_epoch(window_start)
        lg.debug('Set combobox at ' + stage)
        self.idx_stage.setCurrentIndex(STAGE_NAME.index(stage))

    def reset(self):
        self.annot = None
        self.dataset_markers = None
