from logging import getLogger
lg = getLogger(__name__)

from numpy import asarray, max, abs
from scipy.signal import butter, filtfilt, hilbert
from PySide.QtCore import Qt
from PySide.QtGui import (QBrush,
                          QColor,
                          QGraphicsRectItem,
                          QPen,
                          QFormLayout,
                          QPushButton,
                          QGridLayout,
                          QLineEdit,
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

        self.filter = (None, None)
        self.thres_det = None
        self.thres_sel = None
        self.min_dur = None
        self.max_dur = None

        self.idx_filter0 = None
        self.idx_filter1 = None
        self.idx_thres_det = None
        self.idx_thres_sel = None
        self.idx_min_dur = None
        self.idx_max_dur = None
        self.idx_rect = []

        self.create_detect()

    def create_detect(self):
        """Create the widget with the elements that won't change."""
        lg.debug('Creating Detect widget')

        l_left = QFormLayout()
        self.idx_filter0 = QLineEdit(str(self.filter[0]))
        l_left.addRow('Low Filter (Hz)', self.idx_filter0)
        self.idx_thres_det = QLineEdit(str(self.thres_det))
        l_left.addRow('Detection', self.idx_thres_det)
        self.idx_min_dur = QLineEdit(str(self.min_dur))
        l_left.addRow('Min Dur', self.idx_min_dur)

        l_right = QFormLayout()
        self.idx_filter1 = QLineEdit(str(self.filter[1]))
        l_right.addRow('High Filter (Hz)', self.idx_filter1)
        self.idx_thres_sel = QLineEdit(str(self.thres_sel))
        l_right.addRow('Selection', self.idx_thres_sel)
        self.idx_max_dur = QLineEdit(str(self.max_dur))
        l_right.addRow('Max Dur', self.idx_max_dur)

        apply_button = QPushButton('Apply')
        apply_button.clicked.connect(self.update_detect)

        layout = QGridLayout()
        layout.addLayout(l_left, 0, 0)
        layout.addLayout(l_right, 0, 1)
        layout.addWidget(apply_button, 2, 1)
        self.setLayout(layout)

    def update_detect(self):
        """Update the attributes once the dataset has been read in memory.

        """
        lg.debug('Updating Detect widget')

        self.filter = asarray((float(self.idx_filter0.text()),
                               float(self.idx_filter1.text())))
        self.thres_det = float(self.idx_thres_det.text())
        self.thres_sel = float(self.idx_thres_sel.text())
        self.min_dur = float(self.idx_min_dur.text())
        self.max_dur = float(self.idx_max_dur.text())

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

        for rect in self.idx_rect:
            scene.removeItem(rect)

        row = 0
        self.idx_rect = []
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
                    self.idx_rect.append(rect)

                row += 1


def _detect_spindles(dat, time, s_freq, bandpass,
                     thres_det, thres_sel, min_dur, max_dur):

    # filter + hilbert
    nyquist = s_freq / 2
    b, a = butter(FILTER_ORDER, bandpass / nyquist, btype='bandpass')
    dat = abs(hilbert(filtfilt(b, a, dat)))

    return detect_spindle_core(dat, thres_det, dat, thres_sel, time,
                               min_dur, max_dur)
