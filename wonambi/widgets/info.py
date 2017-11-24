"""Widget with general information about the dataset."""
from datetime import timedelta
from functools import partial
from logging import getLogger
from os.path import basename, dirname

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QAction,
                             QFileDialog,
                             QFormLayout,
                             QGroupBox,
                             QLabel,
                             QPushButton,
                             QVBoxLayout,
                             QWidget,
                             )

from .. import Dataset
from .utils import (short_strings, ICON, keep_recent_datasets,
                    choose_file_or_dir)

lg = getLogger(__name__)
settings = QSettings("wonambi", "wonambi")


class Info(QWidget):
    """Display information about the dataset.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    filename : str
        the full path of the file.
    dataset : instance of wonambi.Dataset
        the dataset already read in.
    markers : list
        list of the markers in the dataset

    idx_filename : QPushButton
        button to select dataset / show current dataset
    idx_s_freq : QLabel
        show sampling frequency
    idx_n_chan : QLabel
        show number of channels
    idx_start_time : QLabel
        show start time of the dataset
    idx_end_time : QLabel
        show end time of the dataset

    idx_start : QLabel
        show start time of the window
    idx_length : QLabel
        show length of the time window
    idx_scaling : QLabel
        show current scaling
    idx_distance : QLabel
        show current distance between traces
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.filename = None
        self.dataset = None
        self.markers = []

        # about the recordings
        self.idx_filename = None
        self.idx_s_freq = None
        self.idx_n_chan = None
        self.idx_start_time = None
        self.idx_end_time = None
        # about the visualization
        self.idx_start = None
        self.idx_length = None
        self.idx_scaling = None
        self.idx_distance = None

        self.create()
        self.create_action()

    def create(self):
        """Create the widget layout with all the information."""
        b0 = QGroupBox('Dataset')
        form = QFormLayout()
        b0.setLayout(form)

        open_rec = QPushButton('Open Dataset...')
        open_rec.clicked.connect(self.open_dataset)
        open_rec.setToolTip('Click here to open a new recording')
        self.idx_filename = open_rec
        self.idx_s_freq = QLabel('')
        self.idx_n_chan = QLabel('')
        self.idx_start_time = QLabel('')
        self.idx_end_time = QLabel('')

        form.addRow('Filename:', self.idx_filename)
        form.addRow('Sampl. Freq:', self.idx_s_freq)
        form.addRow('N. Channels:', self.idx_n_chan)
        form.addRow('Start Time: ', self.idx_start_time)
        form.addRow('End Time: ', self.idx_end_time)

        b1 = QGroupBox('View')
        form = QFormLayout()
        b1.setLayout(form)

        self.idx_start = QLabel('')
        self.idx_start.setToolTip('Start time in seconds from the beginning of'
                                  ' the recordings')
        self.idx_length = QLabel('')
        self.idx_length.setToolTip('Duration of the time window in seconds')
        self.idx_scaling = QLabel('')
        self.idx_scaling.setToolTip('Global scaling for all the channels')
        self.idx_distance = QLabel('')
        self.idx_distance.setToolTip('Visual distances between the traces of '
                                     'individual channels')

        form.addRow('Start Time:', self.idx_start)
        form.addRow('Length:', self.idx_length)
        form.addRow('Scaling:', self.idx_scaling)
        form.addRow('Distance:', self.idx_distance)

        layout = QVBoxLayout()
        layout.addWidget(b0)
        layout.addWidget(b1)

        self.setLayout(layout)

    def create_action(self):
        """Create actions associated with this widget.

        Notes
        -----
        I think that this should be a function or a property.

        The good thing about the property is that it is updated every time you
        run it (for example, if you change some parameters in the settings).
        The main drawback is that you cannot reference back to the QAction, as
        it creates new ones every time.
        """
        output = {}

        act = QAction(QIcon(ICON['open_rec']), 'Open Dataset...', self)
        act.setShortcut(QKeySequence.Open)
        act.triggered.connect(self.open_dataset)
        output['open_dataset'] = act

        max_dataset_history = self.parent.value('max_dataset_history')
        recent_recs = keep_recent_datasets(max_dataset_history)

        act = []
        for one_recent_rec in recent_recs:
            act_recent = QAction(one_recent_rec, self)
            act_recent.triggered.connect(partial(self.open_dataset,
                                                 one_recent_rec))
            act.append(act_recent)
        output['open_recent'] = act

        self.action = output

    def open_dataset(self, recent=None, debug_filename=None):
        """Open a new dataset.

        Parameters
        ----------
        recent : path to file
            one of the recent datasets to read
        """
        if recent:
            filename = recent

        elif debug_filename is not None:
            filename = debug_filename

        else:
            try:
                dir_name = dirname(self.filename)
            except (AttributeError, TypeError):
                dir_name = self.parent.value('recording_dir')

            file_or_dir = choose_file_or_dir()
            if file_or_dir == 'dir':
                filename = QFileDialog.getExistingDirectory(self,
                                                            'Open directory',
                                                            dir_name)
            elif file_or_dir == 'file':
                filename, _ = QFileDialog.getOpenFileName(self, 'Open file',
                                                          dir_name)

            elif file_or_dir == 'abort':
                return

        if filename == '':
            return

        # clear previous dataset once the user opens another dataset
        if self.dataset is not None:
            self.parent.reset()

        self.parent.statusBar().showMessage('Reading dataset: ' +
                                            basename(filename))
        lg.info('Reading dataset: ' + str(filename))
        try:
            self.filename = filename
            self.dataset = Dataset(filename)
        except FileNotFoundError:
            msg = 'File ' + basename(filename) + ' cannot be read'
            self.parent.statusBar().showMessage(msg)
            lg.info(msg)
            return

        except BaseException as err:
            self.parent.statusBar().showMessage(str(err))
            lg.info('Error ' + str(err))
            return

        self.parent.statusBar().showMessage('')

        self.parent.update()

    def display_dataset(self):
        """Update the widget with information about the dataset."""
        header = self.dataset.header

        self.parent.setWindowTitle(basename(self.filename))
        short_filename = short_strings(basename(self.filename))
        self.idx_filename.setText(short_filename)
        self.idx_s_freq.setText(str(header['s_freq']))
        self.idx_n_chan.setText(str(len(header['chan_name'])))
        start_time = header['start_time'].strftime('%b-%d %H:%M:%S')
        self.idx_start_time.setText(start_time)
        end_time = (header['start_time'] +
                    timedelta(seconds=header['n_samples'] / header['s_freq']))
        self.idx_end_time.setText(end_time.strftime('%b-%d %H:%M:%S'))

    def display_view(self):
        """Update information about the size of the traces."""
        self.idx_start.setText(str(self.parent.value('window_start')))
        self.idx_length.setText(str(self.parent.value('window_length')))
        self.idx_scaling.setText(str(self.parent.value('y_scale')))
        self.idx_distance.setText(str(self.parent.value('y_distance')))

    def reset(self):
        """Reset widget to original state."""
        self.filename = None
        self.dataset = None

        # about the recordings
        self.idx_filename.setText('Open Recordings...')
        self.idx_s_freq.setText('')
        self.idx_n_chan.setText('')
        self.idx_start_time.setText('')
        self.idx_end_time.setText('')

        # about the visualization
        self.idx_scaling.setText('')
        self.idx_distance.setText('')
        self.idx_length.setText('')
        self.idx_start.setText('')
