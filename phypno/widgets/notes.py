"""Widgets containing notes (such as markers, events, and stages).

  - markers are unique (might have the same text), are not mutually
    exclusive, do not have duration
  - events are not unique, are not mutually exclusive, have variable duration
  - stages are not unique, are mutually exclusive, have fixed duration

"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import datetime, timedelta
from math import floor
from os.path import basename


from PyQt4.QtGui import (QAbstractItemView,
                         QAction,
                         QFormLayout,
                         QGroupBox,
                         QHBoxLayout,
                         QLabel,
                         QListWidget,
                         QPushButton,
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

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.config = ConfigNotes(lambda: None)
        self.annot = None

        self.idx_annotations = None
        self.idx_rater = None

        self.create_notes()

    def create_notes(self):
        b0 = QGroupBox('Annotations')
        form = QFormLayout()
        b0.setLayout(form)

        self.idx_annotations = QPushButton('Load Annotation File...')
        self.idx_annotations.clicked.connect(self.parent.action_load_annot)
        self.idx_rater = QLabel('Rater')

        form.addRow('Annotations File:', self.idx_annotations)
        form.addRow('Rater:', self.idx_rater)

        layout = QVBoxLayout()
        layout.addWidget(b0)

        self.setLayout(layout)

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
        self.display_notes()

    def display_notes(self):
        """Display information about scores and raters."""
        self.idx_annotations.setText(basename(self.annot.xml_file))
        try:
            self.idx_rater.setText(self.annot.current_rater)
        except IndexError:
            self.idx_rater.setText('')


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
