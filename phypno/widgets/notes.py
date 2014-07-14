"""Widgets containing notes (such as markers, events, and stages).

  - markers are unique (might have the same text), are not mutually
    exclusive, do not have duration
  - events are not unique, are not mutually exclusive, have variable duration
  - stages are not unique, are mutually exclusive, have fixed duration

"""
from logging import getLogger
lg = getLogger(__name__)

from functools import partial
from os.path import basename


from PyQt4.QtGui import (QAbstractItemView,
                         QAction,
                         QComboBox,
                         QFormLayout,
                         QGroupBox,
                         QHBoxLayout,
                         QIcon,
                         QLabel,
                         QListWidget,
                         QPushButton,
                         QTableView,
                         QTableWidget,
                         QToolButton,
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

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.config = ConfigNotes(lambda: None)
        self.annot = None

        self.idx_annotations = None
        self.idx_rater = None

        self.idx_event = None
        self.idx_eventtype = None
        self.idx_stage = None

        self.create_notes()

    def create_notes(self):

        self.idx_event = QToolButton(self)
        self.idx_event.setCheckable(True)
        self.idx_eventtype = QComboBox(self)
        self.idx_stage = QComboBox(self)
        self.idx_stage.activated.connect(self.get_sleepstage)

        self.idx_annotations = QPushButton('Load Annotation File...')
        self.idx_annotations.clicked.connect(self.parent.action_load_annot)
        self.idx_rater = QLabel('')

        form = QFormLayout()
        form.addRow('Annotations File:', self.idx_annotations)
        form.addRow('Rater:', self.idx_rater)

        layout = QVBoxLayout()
        layout.addLayout(form)

        self.setLayout(layout)

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

        self.display_notes()

    def display_notes(self):
        """Display information about scores and raters."""
        self.idx_annotations.setText(basename(self.annot.xml_file))
        try:
            self.idx_rater.setText(self.annot.current_rater)
        except IndexError:
            self.idx_rater.setText('')

        for epoch in self.annot.epochs:
            self.parent.overview.mark_stages(epoch['start'],
                                             epoch['end'] -
                                             epoch['start'],
                                             epoch['stage'])

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
        self.parent.action_page_next()

    def set_combobox_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.overview.config.value['window_start']
        stage = self.annot.get_stage_for_epoch(window_start)
        lg.debug('Set combobox at ' + stage)
        self.idx_stage.setCurrentIndex(STAGE_NAME.index(stage))


class Markers(QTableWidget):
    """Visualize markers.

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

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Time', 'Text'])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # TODO: doubleclick

    def update_markers(self, header):
        """Update the markers info."""
        self.display_markers()

    def display_markers(self):
        """Update the table with markers."""
        pass


class Events(QWidget):
    """

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



