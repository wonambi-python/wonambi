"""Widget with general information about the dataset.

"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta
from os.path import basename

from PyQt4.QtGui import (QFormLayout,
                          QLabel,
                          QPushButton,
                          QWidget,
                          )
from .. import Dataset


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
    idx_text : dict of instances of QLabel/QPushButton
        Elements where you should setText once dataset is loaded.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.filename = None
        self.dataset = None

        self.idx_text = {}
        self.idx_amplitude = None
        self.idx_distance = None
        self.idx_length = None

        self.create_info()

    def create_info(self):
        """Create the QFormLayout with all the information."""
        layout = QFormLayout()
        self.setLayout(layout)

        widget = QPushButton('Click here to open a new file')
        widget.clicked.connect(self.parent.action_open_rec)
        widget.setToolTip('Click here to open a new file')
        self.idx_text['filename'] = widget
        self.idx_text['s_freq'] = QLabel('')
        self.idx_text['n_chan'] = QLabel('')
        self.idx_text['start_time'] = QLabel('')
        self.idx_text['end_time'] = QLabel('')
        self.idx_amplitude = QLabel('')
        self.idx_distance = QLabel('')
        self.idx_length = QLabel('')

        layout.addRow('Filename:', self.idx_text['filename'])
        layout.addRow('Sampl. Freq:', self.idx_text['s_freq'])
        layout.addRow('N. Channels:', self.idx_text['n_chan'])
        layout.addRow('Start Time: ', self.idx_text['start_time'])
        layout.addRow('End Time: ', self.idx_text['end_time'])

        layout.addRow('Amplitude:', self.idx_amplitude)
        layout.addRow('Distance:', self.idx_distance)
        layout.addRow('Length:', self.idx_length)

        self.setLayout(layout)

    def update_info(self, filename):
        """Read dataset from filename.

        Parameters
        ----------
        filename : str
            path to file to read.

        """
        lg.info('Loading ' + filename)
        self.filename = filename
        self.dataset = Dataset(filename)

        self.display_info()

    def display_info(self):
        """Update the widget with information about the dataset."""
        header = self.dataset.header

        self.parent.setWindowTitle(basename(self.filename))
        self.idx_text['filename'].setText(basename(self.filename))
        self.idx_text['s_freq'].setText(str(header['s_freq']))
        self.idx_text['n_chan'].setText(str(len(header['chan_name'])))
        start_time = header['start_time'].strftime('%H:%M:%S')
        self.idx_text['start_time'].setText(start_time)
        end_time = header['start_time'] + timedelta(seconds=header['n_samples']
                                                    / header['s_freq'])
        self.idx_text['end_time'].setText(end_time.strftime('%H:%M:%S'))

    def update_traces_info(self):
        """Update information about the size of the traces."""
        self.idx_amplitude.setText(str(self.parent.traces.y_scale))
        self.idx_distance.setText(str(self.parent.traces.y_distance))
        self.idx_length.setText(str(self.parent.overview.window_length))
