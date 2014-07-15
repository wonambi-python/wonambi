"""Widget with general information about the dataset.

"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta
from os.path import basename

from PyQt4.QtGui import (QFormLayout,
                         QGroupBox,
                         QLabel,
                         QPushButton,
                         QVBoxLayout,
                         QWidget,
                         )
from .. import Dataset
from .utils import short_strings


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
        b0 = QGroupBox('Dataset')
        form = QFormLayout()
        b0.setLayout(form)

        widget = QPushButton('Open Recording...')
        widget.clicked.connect(self.parent.action_open_rec)
        widget.setToolTip('Click here to open a new file')
        self.idx_text['filename'] = widget
        self.idx_text['s_freq'] = QLabel('')
        self.idx_text['n_chan'] = QLabel('')
        self.idx_text['start_time'] = QLabel('')
        self.idx_text['end_time'] = QLabel('')

        form.addRow('Filename:', self.idx_text['filename'])
        form.addRow('Sampl. Freq:', self.idx_text['s_freq'])
        form.addRow('N. Channels:', self.idx_text['n_chan'])
        form.addRow('Start Time: ', self.idx_text['start_time'])
        form.addRow('End Time: ', self.idx_text['end_time'])

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
        short_filename = short_strings(basename(self.filename))
        self.idx_text['filename'].setText(short_filename)
        self.idx_text['s_freq'].setText(str(header['s_freq']))
        self.idx_text['n_chan'].setText(str(len(header['chan_name'])))
        start_time = header['start_time'].strftime('%H:%M:%S')
        self.idx_text['start_time'].setText(start_time)
        end_time = header['start_time'] + timedelta(seconds=header['n_samples']
                                                    / header['s_freq'])
        self.idx_text['end_time'].setText(end_time.strftime('%H:%M:%S'))

    def update_traces_info(self):
        """Update information about the size of the traces."""
        self.idx_amplitude.setText(str(self.parent.traces.config.value['y_scale']))
        self.idx_distance.setText(str(self.parent.traces.config.value['y_distance']))
        self.idx_length.setText(str(self.parent.overview.config.value['window_length']))

    def update_annotations(self):
        """Update information about the annotations."""
        self.idx_annotations.setText(str(self.parent.traces.config.value['y_scale']))
        self.idx_rater.setText(str(self.parent.traces.config.value['y_distance']))
