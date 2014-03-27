from logging import getLogger
lg = getLogger(__name__)

from numpy import asarray, max, abs, where
from PySide.QtCore import Qt
from PySide.QtGui import (QBrush,
                          QColor,
                          QGraphicsRectItem,
                          QFormLayout,
                          QPushButton,
                          QGridLayout,
                          QLineEdit,
                          QWidget)

from ..trans import Math, Filter
from ..detect import DetectSpindle

FILTER_ORDER = 4
TRIAL = 0


class Detect(QWidget):
    """Widget to detect spindles.

    Attributes
    ----------
    parent : instance of QMainWindow
        The main window.

        self.filter = (float(preferences['detect/filter'][0]),
                       float(preferences['detect/filter'][1]))
        self.thres_det = float(preferences['detect/thres_det'])
        self.thres_sel = float(preferences['detect/thres_sel'])
        self.min_dur = float(preferences['detect/dur'][0])
        self.max_dur = float(preferences['detect/dur'][1])

        self.idx_filter0 = None
        self.idx_filter1 = None
        self.idx_thres_det = None
        self.idx_thres_sel = None
        self.idx_min_dur = None
        self.idx_max_dur = None
        self.idx_rect = []

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        preferences = self.parent.preferences.values
        self.filter = (float(preferences['detect/filter'][0]),
                       float(preferences['detect/filter'][1]))
        self.thres_det = float(preferences['detect/thres_det'])
        self.thres_sel = float(preferences['detect/thres_sel'])
        self.min_dur = float(preferences['detect/dur'][0])
        self.max_dur = float(preferences['detect/dur'][1])

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
        data = self.parent.traces.data
        y_scale = self.parent.traces.y_scale
        y_distance = self.parent.traces.y_distance

        for rect in self.idx_rect:
            if rect in scene.items():
                scene.removeItem(rect)

        spindles = _detect_spindles(data,
                                    self.filter,
                                    self.thres_det, self.thres_sel,
                                    self.min_dur, self.max_dur)

        self.idx_rect = []
        for sp in spindles:
            lg.info('Adding spindle between {0: 5.3}-{1: 5.3} for chan {2}'
                    ''.format(sp['start_time'], sp['end_time'],
                              sp['chan']))
            row = where(data.axis['chan'][0] == sp['chan'])[0]
            max_data = max(abs(data(trial=TRIAL, chan=sp['chan'])))
            y_value = max_data * y_scale

            rect = QGraphicsRectItem(sp['start_time'],
                                     -y_value,
                                     sp['end_time'] - sp['start_time'],
                                     y_value * 2)
            scene.addItem(rect)
            rect.setBrush(QBrush(QColor(255, 0, 0, 100)))
            rect.setPen(Qt.NoPen)
            rect.setPos(0, y_distance * row + y_distance / 2)
            self.idx_rect.append(rect)


def _detect_spindles(data, bandpass, thres_det, thres_sel, min_dur, max_dur):
    """Detect spindle using hilbert and relative thresholds.

    Parameters
    ----------
    data : instance of ChanTime
        the data ready to be detected
    bandpass : tuple
        frequencies for the bandpass filter
    thres_det : float
        threshold used for spindle detection
    thres_sel : float
        threshold used for spindle selection
    min_dur : float
        minimal duration of the spindle
    max_dur : float
        maximal duration of the spindle

    Returns
    -------
    ndarray
        2 x nSpindles array with absolute time of the spindles.

    Notes
    -----
    Consider including this function in the main phypno repo. It's pretty
    neat, the main problem I have with it is that the interface is not clean
    enough.

    """
    # 1. filter the data
    apply_filter = Filter(low_cut=bandpass[0], high_cut=bandpass[1],
                          s_freq=data.s_freq)
    filtered = apply_filter(data)

    # 2. define relative thresholds
    get_mean = Math(operator_name='mean', axis='time')
    get_std = Math(operator_name='std', axis='time')

    envelope_mean = get_mean(filtered)
    envelope_std = get_std(filtered)

    detection_threshold = (envelope_mean(trial=0) +
                           envelope_std(trial=0) * thres_det)
    selection_threshold = (envelope_mean(trial=0) +
                           envelope_std(trial=0) * thres_sel)

    # 3. prepare detection function
    det_sp = DetectSpindle(threshold_type='relative',
                           detection_threshold=detection_threshold,
                           selection_threshold=selection_threshold,
                           minimal_duration=min_dur,
                           maximal_duration=max_dur)

    # 4. detect spindles on hilbert transform
    apply_abs_hilb = Math(operator_name=('hilbert', 'abs'), axis='time')
    spindle_envelope = apply_abs_hilb(filtered)

    spindles = det_sp(spindle_envelope)

    return spindles.spindle
