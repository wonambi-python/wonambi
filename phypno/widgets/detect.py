"""Widgets to help with the detection of graphoelements during sleep.

"""
from logging import getLogger
lg = getLogger(__name__)

from numpy import max, abs, where
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QBrush,
                         QColor,
                         QComboBox,
                         QGraphicsRectItem,
                         QFormLayout,
                         QPushButton,
                         QGridLayout,
                         QLineEdit,
                         QPen,
                         QWidget,
                         )

from ..detect import DetectSpindle

NoPen = QPen()
NoPen.setStyle(Qt.NoPen)

TRIAL = 0
GRAPHOELEMENTS = ('spindles', )
METHODS = ('UCSD', 'Nir2011', 'Wamsley2012', 'Ferrarelli2007')


class Detect(QWidget):
    """Widget to detect spindles.

    Attributes
    ----------
    parent : instance of QMainWindow
        The main window.
    detfun : instance of DetectSpindles
        function used to detect graphoelements
    idx_grapho : instance of QComboBox
        combobox with list of graphoelements (such as spindles etc)
    idx_method : instance of QComboBox
        combobox with list of methods
    idx_freq0 : instance of QLineEdit
        text to define low frequency for bandpass filter
    idx_freq1 : instance of QLineEdit
        text to define high frequency for bandpass filter
    idx_det_value : instance of QLineEdit
        text to define the detection threshold or peak width
    idx_sel_value : instance of QLineEdit
        text to define the selection threshold or selection width
    idx_min_dur : instance of QLineEdit
        text to define the minimal duration in s
    idx_max_dur : instance of QLineEdit
        text to define the maximal duration in s
    idx_rect : list of instances of QGraphicsRectItem
        rectangles with detected spindles

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.detfun = None

        self.idx_grapho = None
        self.idx_method = None
        self.idx_freq0 = None
        self.idx_freq1 = None
        self.idx_det_value = None
        self.idx_sel_value = None
        self.idx_min_dur = None
        self.idx_max_dur = None
        self.idx_rect = []

        self.create_detect()

    def create_detect(self):
        """Create the widget with the elements that won't change."""
        l_left = QFormLayout()
        self.idx_grapho = QComboBox()
        self.idx_grapho.addItems(GRAPHOELEMENTS)
        self.idx_grapho.setCurrentIndex(0)
        l_left.addRow(self.idx_grapho)

        self.idx_freq0 = QLineEdit('')
        l_left.addRow('Low Filter (Hz)', self.idx_freq0)
        self.idx_det_value = QLineEdit('')
        l_left.addRow('Detection', self.idx_det_value)
        self.idx_min_dur = QLineEdit('')
        l_left.addRow('Min Dur', self.idx_min_dur)

        method = self.parent.preferences.values['detect/spindle_method']
        l_right = QFormLayout()
        self.idx_method = QComboBox()
        self.idx_method.addItems(METHODS)
        self.idx_method.setCurrentIndex(METHODS.index(method))
        self.idx_method.activated.connect(self.reset_method)
        l_right.addRow(self.idx_method)

        self.idx_freq1 = QLineEdit('')
        l_right.addRow('High Filter (Hz)', self.idx_freq1)
        self.idx_sel_value = QLineEdit('')
        l_right.addRow('Selection', self.idx_sel_value)
        self.idx_max_dur = QLineEdit('')
        l_right.addRow('Max Dur', self.idx_max_dur)

        apply_button = QPushButton('Apply')
        apply_button.clicked.connect(self.run_detect)

        layout = QGridLayout()
        layout.addLayout(l_left, 0, 0)
        layout.addLayout(l_right, 0, 1)
        layout.addWidget(apply_button, 2, 1)
        self.setLayout(layout)

        self.update_detect()

    def reset_method(self):
        """Reset all options to default when selecting a new method."""
        self.idx_freq0.setText('')
        self.idx_freq1.setText('')
        self.idx_det_value.setText('')
        self.idx_sel_value.setText('')
        self.idx_min_dur.setText('')
        self.idx_max_dur.setText('')

        self.update_detect()

    def update_detect(self):
        """Read values, if available, and create function for detections."""
        method = self.idx_method.currentText()

        freq0 = self.idx_freq0.text()
        freq1 = self.idx_freq1.text()
        if freq0 == '' or freq1 == '':
            frequency = None
        else:
            frequency = (float(freq0), float(freq1))

        dur0 = self.idx_min_dur.text()
        dur1 = self.idx_max_dur.text()
        if dur0 == '' or dur1 == '':
            duration = None
        else:
            duration = (float(dur0), float(dur1))

        self.detfun = DetectSpindle(method=method, frequency=frequency,
                                    duration=duration)

        det_value = self.idx_det_value.text()
        if not det_value == '':
            self.detfun.det_thresh = float(det_value)

        sel_value = self.idx_sel_value.text()
        if not sel_value == '':
            self.detfun.sel_thresh = float(sel_value)

        self.display_detect()

    def display_detect(self):
        """Update the widgets with the information of the detection method."""
        self.idx_freq0.setText(str(self.detfun.frequency[0]))
        self.idx_freq1.setText(str(self.detfun.frequency[1]))
        self.idx_det_value.setText(str(self.detfun.det_thresh))
        self.idx_sel_value.setText(str(self.detfun.sel_thresh))
        self.idx_min_dur.setText(str(self.detfun.duration[0]))
        self.idx_max_dur.setText(str(self.detfun.duration[1]))

    def run_detect(self):
        """Detect graphoelements, based on info in widget."""
        # update GUI with most current info and create functions for detection
        self.update_detect()

        # keep on working in the same scene as traces
        scene = self.parent.traces.scene
        data = self.parent.traces.data
        y_scale = self.parent.traces.y_scale
        y_distance = self.parent.traces.y_distance

        for rect in self.idx_rect:
            if rect in scene.items():
                scene.removeItem(rect)

        spindles = self.detfun(data)

        self.idx_rect = []
        for sp in spindles.spindle:
            lg.info('Adding spindle between {0: 9.3f}-{1: 9.3f} for chan {2}'
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
            rect.setPen(NoPen)
            rect.setPos(0, y_distance * row + y_distance / 2)
            self.idx_rect.append(rect)
