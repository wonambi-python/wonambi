""" Modal dialogs for carrying out automatic detections.
"""

from logging import getLogger

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QComboBox,
                             QFormLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QVBoxLayout,
                             )

from ..detect import DetectSpindle, DetectSlowWave
from .modal_widgets import ChannelDialog
from .notes import SPINDLE_METHODS, SLOW_WAVE_METHODS
from .utils import FormStr, FormFloat, FormBool, FormMenu

lg = getLogger(__name__)

class SpindleDialog(ChannelDialog):
    """Dialog for specifying spindle detection parameters, ie:
    label, channel, stage, lowcut, highcut, min dur, max dur, detection method,
    wavelet sigma, detection window, smoothing, detection threshold, selection
    threshold, minimum interval, merge across channels.

    Attributes
    ----------
    label : str
        name of event type (to be added to or created)
    method : str
        name of detection method
    idx_method : QComboBox
        Combo box of detection methods.
    """
    def __init__(self, parent):
        ChannelDialog.__init__(self, parent)
        self.setWindowTitle('Spindle detection')
        self.method = None
        self.idx_method = None

        self.create_dialog()

    def create_dialog(self):
        """ Create the dialog."""
        box0 = QGroupBox('Info')

        self.label = FormStr()

        self.label.setText('spin')
        self.idx_group.activated.connect(self.update_channels)
        self.idx_chan.itemSelectionChanged.connect(self.count_channels)

        flayout = QFormLayout(box0)
        flayout.addRow('Label',
                       self.label)
        flayout.addRow('Channel group',
                       self.idx_group)
        flayout.addRow('Channel(s)',
                       self.idx_chan)
        flayout.addRow('Cycle(s)',
                       self.idx_cycle)
        flayout.addRow('Stage(s)',
                       self.idx_stage)

        box1 = QGroupBox('Parameters')

        self.index['f1'] = FormFloat()
        self.index['f2'] = FormFloat()
        self.index['min_dur'] = FormFloat()
        self.index['max_dur'] = FormFloat()
        self.index['sigma'] = FormFloat()
        self.index['win_sz'] = FormFloat()
        self.index['smooth'] = FormFloat()
        self.index['det_thresh_lo'] = FormFloat()
        self.index['det_thresh_hi'] = FormFloat()
        self.index['sel_thresh'] = FormFloat()
        self.index['interval'] = FormFloat()
        self.idx_method = FormMenu(SPINDLE_METHODS)

        self.method = self.idx_method.currentText()
        self.idx_method.currentIndexChanged.connect(self.update_values)

        flayout = QFormLayout(box1)
        flayout.addRow('Method',
                       self.idx_method)
        flayout.addRow('Lowcut (Hz)',
                       self.index['f1'])
        flayout.addRow('Highcut (Hz)',
                       self.index['f2'])
        flayout.addRow('Min. duration (sec)',
                       self.index['min_dur'])
        flayout.addRow(' Max. duration (sec)',
                       self.index['max_dur'])
        flayout.addRow('Wavelet sigma',
                       self.index['sigma'])
        flayout.addRow('Detection window',
                       self.index['win_sz'])
        flayout.addRow('Smoothing',
                       self.index['smooth'])
        flayout.addRow('Detection threshold, low',
                       self.index['det_thresh_lo'])
        flayout.addRow('Detection threshold, high',
                       self.index['det_thresh_hi'])
        flayout.addRow('Selection threshold',
                       self.index['sel_thresh'])
        flayout.addRow('Min. interval',
                       self.index['interval'])

        box3 = QGroupBox('Options')

        self.index['merge'] = FormBool('Merge events across channels')
        self.index['exclude'] = FormBool('Exclude Artefact events')

        self.index['merge'].setCheckState(Qt.Unchecked)
        self.index['merge'].setEnabled(False)
        self.index['exclude'].set_value(True)

        flayout = QFormLayout(box3)
        flayout.addRow(self.index['exclude'])
        flayout.addRow(self.index['merge'])

        self.bbox.clicked.connect(self.button_clicked)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(box1)
        vlayout.addWidget(box3)
        vlayout.addStretch(1)
        vlayout.addLayout(btnlayout)

        hlayout = QHBoxLayout()
        hlayout.addWidget(box0)
        hlayout.addLayout(vlayout)

        self.update_values()
        self.setLayout(hlayout)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            chans = self.get_channels()
            cycle = self.get_cycles()
            stage = self.idx_stage.selectedItems()
            params = {k: v.get_value() for k, v in self.index.items()}

            if None in [params['f1'], params['f2']]:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            if params['max_dur'] is None:
                self.parent.statusBar().showMessage('Specify maximum duration')
                return
            elif params['max_dur'] >= 30:
                self.parent.statusBar().showMessage(
                        'Maximum duration must be below 30 seconds.')
                return

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]
            lg.info('chans= '+str(chans)+' stage= '+str(stage)+' grp= '+str(self.one_grp))

            self.parent.notes.read_data(chans, self.one_grp, period=cycle,
                                        stage=stage, qual='Good',
                                        exclude_artf=params['exclude'])
            if self.parent.notes.data is not None:
                self.parent.notes.detect_events(self.method, params,
                                                label=self.label.get_value())

            self.accept()

        if button is self.idx_cancel:
            self.reject()

        if button is self.idx_help:
            self.parent.show_spindle_help()

    def update_values(self):
        """Update form values when detection method is selected."""
        self.method = self.idx_method.currentText()
        spin_det = DetectSpindle(method=self.method)

        if self.method in ['Wamsley2012', 'UCSD']:
            self.index['win_sz'].set_value(spin_det.det_wavelet['dur'])
        else:
            self.index['win_sz'].set_value(spin_det.moving_rms['dur'])

        self.index['f1'].set_value(spin_det.frequency[0])
        self.index['f2'].set_value(spin_det.frequency[1])
        self.index['min_dur'].set_value(spin_det.duration[0])
        self.index['max_dur'].set_value(spin_det.duration[1])
        self.index['sigma'].set_value(spin_det.det_wavelet['sd'])
        self.index['smooth'].set_value(spin_det.smooth['dur'])
        self.index['det_thresh_lo'].set_value(spin_det.det_thresh_lo)
        self.index['det_thresh_hi'].set_value(spin_det.det_thresh_hi)
        self.index['sel_thresh'].set_value(spin_det.sel_thresh)
        self.index['interval'].set_value(spin_det.min_interval)

        for param in ['sigma', 'win_sz', 'det_thresh_lo', 'det_thresh_hi',
                      'sel_thresh', 'smooth']:
            widg = self.index[param]
            if widg.get_value() == 0:
                widg.set_value('N/A')
                widg.setEnabled(False)
            else:
                widg.setEnabled(True)

    def count_channels(self):
        """If more than one channel selected, activate merge checkbox."""
        merge = self.index['merge']

        if len(self.idx_chan.selectedItems()) > 1:
            if merge.isEnabled():
                return
            else:
                merge.setEnabled(True)
        else:
            self.index['merge'].setCheckState(Qt.Unchecked)
            self.index['merge'].setEnabled(False)


class SWDialog(ChannelDialog):
    """Dialog for specifying SW detection parameters, ie:
    label, channel, stage, min dur, max dur, detection method, lowcut, highcut,
    minimum and maximum trough duration, maximum trough amplitude, minimum
    peak-to-peak amplitude.

    Attributes
    ----------
    label : str
        name of event type (to be added to or created)
    method : str
        name of detection method
    idx_method : QComboBox
        Combo box of detection methods.
    """
    def __init__(self, parent):
        ChannelDialog.__init__(self, parent)
        self.setWindowTitle('Slow wave detection')
        self.idx_method = None

        self.create_dialog()

    def create_dialog(self):
        """ Create the dialog."""
        box0 = QGroupBox('Info')

        self.label = FormStr()

        self.label.setText('sw')
        self.idx_group.activated.connect(self.update_channels)

        flayout = QFormLayout()
        box0.setLayout(flayout)
        flayout.addRow('Label',
                           self.label)
        flayout.addRow('Channel group',
                       self.idx_group)
        flayout.addRow('Channel(s)',
                       self.idx_chan)
        flayout.addRow('Cycle(s)',
                       self.idx_cycle)
        flayout.addRow('Stage(s)',
                       self.idx_stage)

        box1 = QGroupBox('Parameters')

        mbox = QComboBox()
        method_list = SLOW_WAVE_METHODS
        for method in method_list:
            mbox.addItem(method)
        self.idx_method = mbox
        self.method = mbox.currentText()
        mbox.currentIndexChanged.connect(self.update_values)

        self.index['f1'] = FormFloat()
        self.index['f2'] = FormFloat()
        self.index['min_trough_dur'] = FormFloat()
        self.index['max_trough_dur'] = FormFloat()
        self.index['max_trough_amp'] = FormFloat()
        self.index['min_ptp'] = FormFloat()
        self.index['min_dur'] = FormFloat()
        self.index['max_dur'] = FormFloat()

        flayout = QFormLayout(box1)
        flayout.addRow('Method',
                            mbox)
        flayout.addRow('Lowcut (Hz)',
                           self.index['f1'])
        flayout.addRow('Highcut (Hz)',
                           self.index['f2'])
        flayout.addRow('Min. trough duration (sec)',
                           self.index['min_trough_dur'])
        flayout.addRow(' Max. trough duration (sec)',
                           self.index['max_trough_dur'])
        flayout.addRow(' Max. trough amplitude (uV)',
                           self.index['max_trough_amp'])
        flayout.addRow('Min. peak-to-peak amplitude (uV)',
                           self.index['min_ptp'])
        flayout.addRow('Min. duration (sec)',
                           self.index['min_dur'])
        flayout.addRow(' Max. duration (sec)',
                           self.index['max_dur'])
        box3 = QGroupBox('Options')

        self.index['demean'] = FormBool('De-mean (by channel mean)')
        self.index['exclude'] = FormBool('Exclude Artefact events')
        self.index['invert'] = FormBool('Invert detection')

        self.index['demean'].set_value(True)
        self.index['exclude'].set_value(True)

        flayout = QFormLayout(box3)
        flayout.addRow(self.index['demean'])
        flayout.addRow(self.index['exclude'])
        flayout.addRow(self.index['invert'])

        self.bbox.clicked.connect(self.button_clicked)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(box1)
        vlayout.addWidget(box3)
        vlayout.addStretch(1)
        vlayout.addLayout(btnlayout)

        hlayout = QHBoxLayout()
        hlayout.addWidget(box0)
        hlayout.addLayout(vlayout)

        self.update_values()
        self.setLayout(hlayout)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            chans = self.get_channels()
            cycle = self.get_cycles()
            stage = self.idx_stage.selectedItems()
            params = {k: v.get_value() for k, v in self.index.items()}

            if None in [params['f1'], params['f2']]:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]

            self.parent.notes.read_data(chans, self.one_grp, period=cycle,
                                        stage=stage, qual='Good',
                                        demean=params['demean'],
                                        exclude_artf=params['exclude'])

            if self.parent.notes.data is not None:
                self.parent.notes.detect_events(self.method, params,
                                                label=self.label.get_value())

            self.accept()

        if button is self.idx_cancel:
            self.reject()

        if button is self.idx_help:
            self.parent.show_slowwave_help()
            pass

    def update_values(self):
        """Update form values when detection method is selected."""
        self.method = self.idx_method.currentText()
        sw_det = DetectSlowWave(method=self.method)

        self.index['f1'].set_value(sw_det.det_filt['freq'][0])
        self.index['f2'].set_value(sw_det.det_filt['freq'][1])
        self.index['min_trough_dur'].set_value(sw_det.trough_duration[0])
        self.index['max_trough_dur'].set_value(sw_det.trough_duration[1])
        self.index['max_trough_amp'].set_value(sw_det.max_trough_amp)
        self.index['min_ptp'].set_value(sw_det.min_ptp)
        self.index['min_dur'].set_value(sw_det.min_dur)
        self.index['max_dur'].set_value(sw_det.max_dur)
