"""Widgets containing notes (such as markers, events, and stages).

  - markers are unique (might have the same text), are not mutually
    exclusive, do not have duration
  - events are not unique, are not mutually exclusive, have variable duration
  - stages are not unique, are mutually exclusive, have fixed duration

"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import datetime, timedelta
from functools import partial
from math import floor
from os.path import basename


from PyQt4.QtGui import (QAbstractItemView,
                         QAction,
                         QFormLayout,
                         QGroupBox,
                         QHBoxLayout,
                         QListWidget,
                         QTableView,
                         QTableWidget,
                         QTableWidgetItem,
                         QWidget,
                         QVBoxLayout,
                         )

from ..attr import Annotations, create_empty_annotations

from .settings import Config, FormInt

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


class Notes(QWidget):
    """Widget that contains information about sleep scoring.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    scores : instance of Scores
        information about sleep staging
    idx_filename : instance of QPushButton
        push button to open a new file
    idx_rater : instance of QLabel
        widget wit the name of the rater
    idx_stages : instance of QComboBox
        widget with the possible sleep stages
    action : dict
        names of all the actions related to sleep scoring

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.config = ConfigNotes(lambda: None)
        self.action = {}
        self.notes = None

        layout = QFormLayout()
        self.setLayout(layout)

    def update_notes(self, xml_file, new):
        """Update information about the sleep scoring.

        Parameters
        ----------
        xml_file : str
            file of the new or existing .xml file

        """
        if new:
            create_empty_annotations(xml_file, self.parent.info.dataset)
            self.notes = Annotations(xml_file)
        else:
            self.notes = Annotations(xml_file)

        self.create_actions()
        # self.display_stages()

    def display_stages(self):
        """Update the widgets of the sleep scoring."""
        self.idx_filename.setText(basename(self.scores.xml_file))
        self.idx_rater.setText(self.scores.get_rater())
        for one_stage in STAGE_NAME:
            self.idx_stages.addItem(one_stage)

        for epoch in self.scores.epochs:
            self.parent.overview.mark_stages(epoch['start_time'],
                                             epoch['end_time'] -
                                             epoch['start_time'],
                                             epoch['stage'])

    def create_actions(self):
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

    def get_sleepstage(self, stage_idx=None):
        """Get the sleep stage, using shortcuts or combobox.

        Parameters
        ----------
        stage : str
            string with the name of the sleep stage.

        """
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length

        id_window = str(window_start)
        lg.info('User staged ' + id_window + ' as ' + STAGE_NAME[stage_idx])
        self.scores.set_stage_for_epoch(id_window, STAGE_NAME[stage_idx])
        self.set_combobox_index()
        self.parent.overview.mark_stages(window_start, window_length,
                                         STAGE_NAME[stage_idx])
        self.parent.action_page_next()

    def set_combobox_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.overview.window_start
        stage = self.scores.get_stage_for_epoch(str(window_start))
        lg.debug('Set combobox at ' + stage)
        self.idx_stages.setCurrentIndex(STAGE_NAME.index(stage))


class Markers(QTableWidget):
    """Keep track of all the markers.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    markers : list of dict
        each dict contains time (in s from beginning of file) and name

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.markers = []

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Time', 'Text'])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cellDoubleClicked.connect(self.move_to_marker)

    def update_markers(self, header):
        """Update the markers info

        Parameters
        ----------
        header : dict
            header of the dataset

        """
        markers = []
        splitted = header['orig']['notes'].split('\n')
        for mrk in splitted:
            values = mrk.split(',')
            mrk_time = datetime.strptime(values[0], '%Y-%m-%dT%H:%M:%S')
            mrk_sec = (mrk_time - header['start_time']).total_seconds()

            markers.append({'time': mrk_sec,
                            'name': ','.join(values[2:])
                            })

        self.markers = markers
        self.display_markers()

    def display_markers(self):
        """Update the table with markers."""
        start_time = self.parent.info.dataset.header['start_time']

        self.setRowCount(len(self.markers))
        for i, mrk in enumerate(self.markers):
            abs_time = (start_time +
                        timedelta(seconds=mrk['time'])).strftime('%H:%M:%S')
            self.setItem(i, 0, QTableWidgetItem(abs_time))
            self.setItem(i, 1, QTableWidgetItem(mrk['name']))

        self.parent.overview.mark_markers()

    def move_to_marker(self, row, col):
        """Move to point in time marked by the marker.

        Parameters
        ----------
        row : QtCore.int

        column : QtCore.int

        """
        window_length = self.parent.overview.config.value['window_length']
        marker_time = self.markers[row]['time']
        window_start = floor(marker_time / window_length) * window_length
        self.parent.overview.update_position(window_start)


class Events(QWidget):
    """TODO: this should have checkboxes on the left and the list of selected
    events on the right side

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.idx_stages = QListWidget()
        self.idx_table = QTableView()

        layout = QHBoxLayout()
        layout.addWidget(self.idx_stages)
        layout.addWidget(self.idx_table)
        self.setLayout(layout)

    def update_events(self):
        """

        """

        self.display_events()

    def display_events(self):
        pass
