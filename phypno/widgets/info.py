"""Widget with general information about the dataset."""
from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta
from functools import partial
from os.path import basename, dirname

from PyQt4.QtGui import (QAction,
                         QFormLayout,
                         QGroupBox,
                         QIcon,
                         QKeySequence,
                         QLabel,
                         QFileDialog,
                         QPushButton,
                         QVBoxLayout,
                         QWidget,
                         )

from .. import Dataset
from .utils import (short_strings, ICON, keep_recent_datasets,
                    choose_file_or_dir)


class Info(QWidget):
    """Display information about the dataset.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    filename : str
        the full path of the file.
    dataset : instance of phypno.Dataset
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

    idx_amplitude : QLabel
        show current amplitude
    idx_distance : QLabel
        show current distance between traces
    idx_length : QLabel
        show length of the time window

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
        self.idx_amplitude = None
        self.idx_distance = None
        self.idx_length = None

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

        self.idx_amplitude = QLabel('')
        self.idx_distance = QLabel('')
        self.idx_length = QLabel('')

        form.addRow('Amplitude:', self.idx_amplitude)
        form.addRow('Distance:', self.idx_distance)
        form.addRow('Length:', self.idx_length)

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

    def open_dataset(self, recent=None):
        """Open a new dataset.

        Parameters
        ----------
        recent : path to file
            one of the recent datasets to read

        """
        if self.dataset is not None:
            self.parent.reset()

        if recent:
            filename = recent
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
                filename = QFileDialog.getOpenFileName(self, 'Open file',
                                                       dir_name)
            elif file_or_dir == 'abort':
                return

            if filename == '':
                return

        self.parent.statusBar().showMessage('Reading dataset: ' +
                                            basename(filename))
        try:
            self.filename = filename
            self.dataset = Dataset(filename)

        except FileNotFoundError:
            self.parent.statusBar().showMessage('File ' + basename(filename) +
                                                ' cannot be read')
            return

        except Exception as err:
            self.parent.statusBar().showMessage(str(err))
            raise err

        self.parent.statusBar().showMessage('')

        self.display_dataset()
        self.parent.overview.update()
        self.parent.channels.chan_name = self.dataset.header['chan_name']

        try:
            self.markers = self.dataset.read_markers()
        except FileNotFoundError:
            lg.info('No notes/markers present in the header of the file')
        else:
            self.parent.notes.update_dataset_marker()

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
        end_time = header['start_time'] + timedelta(seconds=header['n_samples']
                                                    / header['s_freq'])
        self.idx_end_time.setText(end_time.strftime('%b-%d %H:%M:%S'))

    def display_view(self):
        """Update information about the size of the traces."""
        self.idx_amplitude.setText(str(self.parent.value('y_scale')))
        self.idx_distance.setText(str(self.parent.value('y_distance')))
        self.idx_length.setText(str(self.parent.value('window_length')))

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
        self.idx_amplitude.setText('')
        self.idx_distance.setText('')
        self.idx_length.setText('')
