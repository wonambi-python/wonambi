from logging import getLogger
lg = getLogger(__name__)

from datetime import datetime, timedelta
from functools import partial
from math import floor
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString
from PySide.QtCore import QSettings
from PySide.QtGui import (QAbstractItemView,
                          QAction,
                          QComboBox,
                          QFormLayout,
                          QPushButton,
                          QLabel,
                          QTableView,
                          QTableWidget,
                          QTableWidgetItem,
                          QWidget,
                          )

config = QSettings('phypno', 'scroll_data')

stage_name = ['Wake', 'REM', 'NREM1', 'NREM2', 'NREM3', 'Unknown']
stage_shortcut = ['6', '5', '1', '2', '3', '0']


class Bookmarks(QTableWidget):
    """Keep track of all the bookmarks.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    bookmarks : list of dict
        each dict contains time (in s from beginning of file) and name

    Notes
    -----
    I haven't been really careful, I use the term "note" sometimes. To be
    precise, bookmark, events, stages are all types of notes.

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.bookmarks = []

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Time', 'Text'])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def update_bookmarks(self, header):
        """Update the bookmarks info

        Parameters
        ----------
        header : dict
            header of the dataset

        """
        bookmarks = []
        splitted = header['orig']['notes'].split('\n')
        for bm in splitted:
            values = bm.split(',')
            bm_time = datetime.strptime(values[0], '%Y-%m-%dT%H:%M:%S')
            bm_sec = (bm_time - header['start_time']).total_seconds()

            bookmarks.append({'time': bm_sec,
                              'name': ','.join(values[2:])
                              })

        self.bookmarks = bookmarks
        self.display_bookmarks()

    def display_bookmarks(self):
        """Update the table with bookmarks."""
        start_time = self.parent.info.dataset.header['start_time']


        self.setRowCount(len(self.bookmarks))
        for i, bm in enumerate(self.bookmarks):
            abs_time = (start_time + timedelta(seconds=bm['time'])).strftime('%H:%M:%S')
            self.setItem(i, 0, QTableWidgetItem(abs_time))
            self.setItem(i, 1, QTableWidgetItem(bm['name']))

        self.parent.overview.mark_bookmarks()


class Events(QWidget):
    """

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.combobox = QComboBox()
        self.table = QTableView()

        layout = QFormLayout()
        layout.addRow('Events: ', self.combobox)
        layout.addRow('List: ', self.table)
        self.setLayout(layout)

    def update_overview(self):
        """

        """

        self.display_overview()

    def display_overview(self):
        pass


class Scores():
    """Class to return nicely formatted information from xml.

    Parameters
    ----------
    xml_file : str
        path to xml file
    root : instance of xml.etree.ElementTree.Element, optional
        xml structure with information about sleep staging

    Attributes
    ----------
    root : instance of xml.etree.ElementTree.Element
        xml structure with information about sleep staging
    xml_file : str
        path to xml file

    Notes
    -----
    If root is not given, xml will be read from file. If both are given, it
    overwrites filename with root.

    """
    def __init__(self, xml_file, root=None):
        self.xml_file = xml_file
        self.root = root

        if root is None:
            self.load()
        else:
            self.save()

    def get_rater(self):
        """Returns the name of the rater.

        Notes
        -----
        TODO: what if we have more raters?

        """
        return list(self.root)[0].get('name')

    def get_epochs(self):
        all_epochs = list(self.root)[0]
        epochs = {}
        for epoch in all_epochs:
            id_epoch = epoch.get('id')
            epochs[id_epoch] = {'start_time': int(list(epoch)[0].text),
                                'end_time': int(list(epoch)[1].text),
                                'stage': list(epoch)[2].text,
                                }
        return epochs

    def get_stage_for_epoch(self, id_epoch):
        """Return stage for one specific epoch.

        Parameters
        ----------
        id_epoch : str
            index of the epoch

        Returns
        -------
        stage : str
            description of the stage.

        """
        all_epochs = list(self.root)[0]
        for epoch in all_epochs:
            if epoch.get('id') == id_epoch:
                break
        return list(epoch)[2].text

    def set_stage_for_epoch(self, id_epoch, stage):
        """Change the stage for one specific epoch.

        Parameters
        ----------
        id_epoch : str
            index of the epoch
        stage : str
            description of the stage.

        """
        all_epochs = list(self.root)[0]
        for epoch in all_epochs:
            if epoch.get('id') == id_epoch:
                list(epoch)[2].text = stage

        self.save()

    def load(self):
        """Load xml from file."""
        xml = parse(self.xml_file)
        root = xml.getroot()
        root.text = root.text.strip()
        for rater in root:
            rater.text = rater.text.strip()
            rater.tail = rater.tail.strip()
            for epochs in rater:
                epochs.text = epochs.text.strip()
                epochs.tail = epochs.tail.strip()
                for values in epochs:
                    values.tail = values.tail.strip()
        self.root = root

    def save(self):
        """Save xml to file."""
        xml = parseString(tostring(self.root))
        with open(self.xml_file, 'w+') as f:
            f.write(xml.toprettyxml())


class Stages(QWidget):
    """Widget that contains about sleep scoring.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    scores : instance of Scores
        information about sleep staging
    filename : str
        path to .xml file
    file_button : instance of QPushButton
        push button to open a new file
    rater : instance of QLabel
        widget wit the name of the rater
    combobox : instance of QComboBox
        widget with the possible sleep stages
    action : dict
        names of all the actions related to sleep scoring

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.action = {}
        self.scores = None
        self.file_button = QPushButton('Click to choose file')
        self.file_button.clicked.connect(parent.action_open_stages)
        self.rater = QLabel()
        self.combobox = QComboBox()
        self.combobox.activated.connect(self.get_sleepstage)
        self.create_actions()

        layout = QFormLayout()
        layout.addRow('Filename: ', self.file_button)
        layout.addRow('Rater: ', self.rater)
        layout.addRow('Stage: ', self.combobox)
        self.setLayout(layout)

    def update_overview(self, xml_file):
        """Update information about the sleep scoring.

        Parameters
        ----------
        xml_file : str
            file of the new or existing .xml file

        """
        try:
            self.scores = Scores(xml_file)
        except FileNotFoundError:
            root = self.create_empty_xml()
            self.scores = Scores(xml_file, root)
        self.display_overview()

    def display_overview(self):
        """Update the widgets of the sleep scoring."""
        self.file_button.setText(self.scores.xml_file)
        self.rater.setText(self.scores.get_rater())
        for one_stage in stage_name:
            self.combobox.addItem(one_stage)
        self.parent.overview.color_stages()

    def create_actions(self):
        """Create actions and shortcut to score sleep."""
        actions = {}
        for one_stage, one_shortcut in zip(stage_name, stage_shortcut):
            actions[one_stage] = QAction('Score as ' + one_stage, self.parent)
            actions[one_stage].setShortcut(one_shortcut)
            stage_idx = stage_name.index(one_stage)
            actions[one_stage].triggered.connect(partial(self.get_sleepstage,
                                                         stage_idx))
            self.addAction(actions[one_stage])
        self.action = actions

    def set_combobox_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.overview.window_start
        stage = self.scores.get_stage_for_epoch(str(window_start))
        self.combobox.setCurrentIndex(stage_name.index(stage))
        self.parent.overview.color_stages()

    def get_sleepstage(self, stage_idx=None):
        """Get the sleep stage, using shortcuts or combobox.

        Parameters
        ----------
        stage : str
            string with the name of the sleep stage.

        """
        id_window = str(self.parent.overview.window_start)
        self.scores.set_stage_for_epoch(id_window, stage_name[stage_idx])
        self.set_combobox_index()
        self.parent.action_page_next()

    def create_empty_xml(self):
        """Create a new empty xml file, to keep the sleep scoring.

        It's organized with sleep_stages (and filename of the dataset), rater
        (with the name of the rater), epochs (with id equal to the start_time),
        which have start_time, end_time, and stage.

        """
        minimum = floor(self.parent.overview.minimum)
        maximum = floor(self.parent.overview.maximum)
        window_length = config.value('stage_scoring_window')

        main = Element('sleep_stages')
        main.set('filename', self.parent.info.filename)
        rated = SubElement(main, 'rater')
        rated.set('name', 'TODO')

        for t in range(minimum, maximum, window_length):
            epoch = SubElement(rated, 'epoch')
            epoch.set('id', str(t))  # use start_time as id

            start_time = SubElement(epoch, 'start_time')
            start_time.text = str(t)

            end_time = SubElement(epoch, 'end_time')
            end_time.text = str(t + window_length)

            stage = SubElement(epoch, 'stage')
            stage.text = 'Unknown'

        return main
