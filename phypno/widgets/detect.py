from logging import getLogger
lg = getLogger(__name__)

from numpy import asarray, max, abs
from scipy.signal import butter, filtfilt, hilbert
from PySide.QtCore import Qt
from PySide.QtGui import (QBrush,
                          QColor,
                          QGraphicsRectItem,
                          QPen,
                          QPushButton,
                          QGridLayout,
                          QWidget)

from ..detect.spindle import _detect_spindles as detect_spindle_core

FILTER_ORDER = 4


class Detect(QWidget):
    """Widget to detect spindles.

    Attributes
    ----------
    parent : instance of QMainWindow
        The main window.
    attributes : type
        explanation

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.thres_det = None
        self.thres_sel = None
        self.min_dur = None
        self.max_dur = None

        self.idx_XXX = []  # list of instances of the objects

        self.create_detect()

    def create_detect(self):
        """Create the widget with the elements that won't change."""
        lg.debug('Creating Detect widget')

        layout = QGridLayout()

        apply_button = QPushButton('Apply')
        apply_button.clicked.connect(self.update_detect)

        layout.addWidget(apply_button, 4, 1)
        self.setLayout(layout)

    def update_detect(self):
        """Update the attributes once the dataset has been read in memory.

        """
        lg.debug('Updating Detect widget')

        self.filter = asarray((11, 18))
        self.thres_det = .1
        self.thres_sel = .05
        self.min_dur = .1
        self.max_dur = 90

        self.display_detect()

    def display_detect(self):
        """Update the widgets with the new information."""
        lg.debug('Displaying Detect widget')

        # keep on working in the same
        scene = self.parent.traces.scene
        time = self.parent.traces.time
        data = self.parent.traces.data
        s_freq = int(self.parent.info.dataset.header['s_freq'])
        y_scale = self.parent.traces.y_scale
        y_distance = self.parent.traces.y_distance

        row = 0
        for one_grp in self.parent.channels.groups:
            for one_chan in one_grp['chan_to_plot']:
                chan_name = one_chan + ' (' + one_grp['name'] + ')'

                spindles = _detect_spindles(data[chan_name], time, s_freq,
                                            self.filter,
                                            self.thres_det, self.thres_sel,
                                            self.min_dur, self.max_dur)

                max_data = max(abs(data[chan_name])) * y_scale

                if spindles is None:
                    lg.info('No spindle found in ' + chan_name)
                    continue

                for sp in spindles:
                    rect = QGraphicsRectItem(sp[0], -max_data,
                                             sp[1] - sp[0],
                                             max_data * 2)
                    scene.addItem(rect)
                    rect.setBrush(QBrush(QColor(255, 0, 0, 100)))
                    rect.setPen(Qt.NoPen)
                    rect.setPos(0, y_distance * row + y_distance / 2)

                row += 1


def _detect_spindles(dat, time, s_freq, bandpass,
                     thres_det, thres_sel, min_dur, max_dur):

    # filter + hilbert
    nyquist = s_freq / 2
    b, a = butter(FILTER_ORDER, bandpass / nyquist, btype='bandpass')
    dat = abs(hilbert(filtfilt(b, a, dat)))

    return detect_spindle_core(dat, thres_det, dat, thres_sel, time,
                               min_dur, max_dur)
