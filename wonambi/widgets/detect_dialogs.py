""" Modal dialogs for carrying out automatic detections.
"""

from logging import getLogger

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QComboBox,
                             QErrorMessage,
                             QFormLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QVBoxLayout,
                             )

from ..detect import DetectSpindle, DetectSlowWave
from ..trans import fetch, math
from .modal_widgets import ChannelDialog
from .notes import SPINDLE_METHODS, SLOW_WAVE_METHODS
from .utils import FormStr, FormFloat, FormBool, FormMenu

lg = getLogger(__name__)

class SpindleDialog(ChannelDialog):
    """Dialog for specifying spindle detection parameters, ie:
    name, channel, stage, lowcut, highcut, min dur, max dur, detection method,
    wavelet sigma, detection window, smoothing, detection threshold, selection
    threshold, minimum interval, merge across channels.

    Attributes
    ----------
    name : str
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

        self.name = FormStr()

        self.name.setText('spin')
        self.idx_group.activated.connect(self.update_channels)
        self.idx_chan.itemSelectionChanged.connect(self.count_channels)

        form = QFormLayout(box0)
        form.addRow('Event name',
                       self.name)
        form.addRow('Channel group',
                       self.idx_group)
        form.addRow('Channel(s)',
                       self.idx_chan)
        form.addRow('Cycle(s)',
                       self.idx_cycle)
        form.addRow('Stage(s)',
                       self.idx_stage)

        box1 = QGroupBox('Parameters')

        self.idx_method = FormMenu(SPINDLE_METHODS)
        self.index['f1'] = FormFloat()
        self.index['f2'] = FormFloat()
        self.index['rolloff'] = FormFloat()
        self.index['tolerance'] = FormFloat()
        self.index['min_dur'] = FormFloat()
        self.index['max_dur'] = FormFloat()
        self.index['interval'] = FormFloat()
        
        self.index['0'] = FormFloat() # sigma
        self.index['1'] = FormFloat() # win_sz
        self.index['2'] = FormFloat() # smooth
        self.index['3'] = FormFloat() # det_thresh
        self.index['4'] = FormFloat() # det_thresh_hi
        self.index['5'] = FormFloat() # sel_thresh
        
        self.label = []
        for i in range(6):
            self.label.append(QLabel(''))

        self.method = self.idx_method.currentText()
        self.idx_method.currentIndexChanged.connect(self.update_values)

        form = QFormLayout(box1)
        form.addRow('Method',
                       self.idx_method)
        form.addRow('Lowcut (Hz)',
                       self.index['f1'])
        form.addRow('Highcut (Hz)',
                       self.index['f2'])
        form.addRow('Roll-off (Hz)',
                       self.index['rolloff'])
        
        form.addRow(self.label[0], self.index['0'])
        form.addRow(self.label[1], self.index['1'])
        form.addRow(self.label[2], self.index['2'])
        form.addRow(self.label[3], self.index['3'])
        form.addRow(self.label[4], self.index['4'])
        form.addRow(self.label[5], self.index['5'])

        form.addRow('Tolerance (sec)',
                       self.index['tolerance'])
        form.addRow('Min. duration (sec)',
                       self.index['min_dur'])
        form.addRow('Max. duration (sec)',
                       self.index['max_dur'])
        form.addRow('Min. interval (sec)',
                       self.index['interval'])
        
        box3 = QGroupBox('Options')

        self.index['detrend'] = FormBool('Detrend (linear)')
        self.index['merge'] = FormBool('Merge events across channels')
        self.index['excl_epoch'] = FormBool('Exclude Poor signal epochs')
        self.index['excl_event'] = FormMenu(['none', 'channel-specific', 
                                      'from any channel'])
        self.index['min_seg_dur'] = FormFloat(5)

        self.index['excl_epoch'].set_value(True)
        self.index['merge'].setCheckState(Qt.Unchecked)
        self.index['merge'].setEnabled(False)

        form = QFormLayout(box3)
        form.addRow(self.index['detrend'])
        form.addRow(self.index['excl_epoch'])
        form.addRow('Exclude Artefact events', 
                    self.index['excl_event'])
        form.addRow('Minimum subsegment duration',
                       self.index['min_seg_dur'])
        form.addRow(self.index['merge'])

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
            group = self.one_grp
            cycle = self.get_cycles()
            stage = self.idx_stage.selectedItems()
            params = {k: v.get_value() for k, v in self.index.items()}
            name = self.name.get_value()

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

            chan_full = None
            reject_artf = False
            if params['excl_event'] == 'channel-specific':
                chan_full = [i + ' (' + self.idx_group.currentText() + ''
                           ')' for i in chans]
                chans = None
                reject_artf = True
            elif params['excl_event'] == 'from any channel':
                reject_artf = True
            
            data = fetch(self.parent.info.dataset, 
                          self.parent.notes.annot, cat=(1, 1, 1, 0),
                          stage=stage, cycle=cycle, 
                          chan_full=chan_full, min_dur=params['min_seg_dur'], 
                          reject_epoch=params['excl_epoch'], 
                          reject_artf=reject_artf)
            
            if not data.segments:
                msg = 'No valid signal found.'
                error_dialog = QErrorMessage(self)
                error_dialog.setWindowTitle('Error fetching data')
                error_dialog.showMessage(msg)
                return
            
            ding = data.read_data(chans, group['ref_chan'], group['name'],
                                  parent=self)
            
            if not ding:
                self.parent.statusBar().showMessage('Process interrupted.')
                return

            data = data[0]['data']
            if params['detrend']:
                data = math(data, operator_name='detrend', axis='time')            
            
            self.parent.notes.detect_events(data, self.method, 
                                            params, label=name)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

    def update_values(self):
        """Update form values when detection method is selected."""
        self.method = self.idx_method.currentText()
        spin_det = DetectSpindle(method=self.method)
        
        self.index['f1'].set_value(spin_det.frequency[0])
        self.index['f2'].set_value(spin_det.frequency[1])
        self.index['tolerance'].set_value(spin_det.tolerance)
        self.index['min_dur'].set_value(spin_det.duration[0])
        self.index['max_dur'].set_value(spin_det.duration[1])        
        self.index['interval'].set_value(spin_det.min_interval)

        if spin_det.rolloff:
            self.index['rolloff'].set_value(spin_det.rolloff)
            self.index['rolloff'].setEnabled(True)
        else:
            self.index['rolloff'].set_value('N/A')
            self.index['rolloff'].setEnabled(False)

        if self.method == 'Ferrarelli2007':
            self.label[0].setText('Detection threshold')
            self.label[1].setText('Selection threshold')
            self.label[2].setText('')
            self.label[3].setText('')
            self.label[4].setText('')
            self.label[5].setText('')

            self.index['0'].set_value(spin_det.det_thresh)
            self.index['1'].set_value(spin_det.sel_thresh)        
        
        if self.method == 'Nir2011':
            self.label[0].setText('Gaussian smoothing sigma (sec)')
            self.label[1].setText('Detection threshold (SD)')
            self.label[2].setText('Selection threshold (SD)')
            self.label[3].setText('')
            self.label[4].setText('')
            self.label[5].setText('')

            self.index['0'].set_value(spin_det.smooth['dur'])
            self.index['1'].set_value(spin_det.det_thresh)
            self.index['2'].set_value(spin_det.sel_thresh)            
        
        if self.method == 'Moelle2011':
            self.label[0].setText('RMS window length (sec)')
            self.label[1].setText('Smoothing window length (sec)')
            self.label[2].setText('Detection threshold (SD)')
            self.label[3].setText('')
            self.label[4].setText('')
            self.label[5].setText('')

            self.index['0'].set_value(spin_det.moving_rms['dur'])
            self.index['1'].set_value(spin_det.smooth['dur'])
            self.index['2'].set_value(spin_det.det_thresh)

        if self.method == 'Wamsley2012':
            self.label[0].setText('Wavelet window length (sec)')
            self.label[1].setText('Wavelet sigma (sec)')
            self.label[2].setText('Smoothing window length (sec)')
            self.label[3].setText('Detection threshold')
            self.label[4].setText('')
            self.label[5].setText('')
            
            self.index['0'].set_value(spin_det.det_wavelet['dur'])
            self.index['1'].set_value(spin_det.det_wavelet['sd'])
            self.index['2'].set_value(spin_det.smooth['dur'])
            self.index['3'].set_value(spin_det.det_thresh)

        if self.method == 'Martin2013':
            self.label[0].setText('RMS window length (sec)')
            self.label[1].setText('RMS window step (sec)')
            self.label[2].setText('Detection threshold (percentile)')
            
            self.index['0'].set_value(spin_det.moving_rms['dur'])
            self.index['1'].set_value(spin_det.moving_rms['step'])
            self.index['2'].set_value(spin_det.det_thresh)
        
        if self.method == 'Ray2015':
            self.label[0].setText('Smoothing window length (sec)')
            self.label[1].setText('z-score window length (sec)')
            self.label[2].setText('Detection threshold (z)')
            self.label[3].setText('Selection threshold (z)')
            self.label[4].setText('')
            self.label[5].setText('')
            
            self.index['0'].set_value(spin_det.smooth['dur'])
            self.index['1'].set_value(spin_det.zscore['step'])
            self.index['2'].set_value(spin_det.det_thresh)
            self.index['3'].set_value(spin_det.sel_thresh)

        if self.method == 'Lacourse2018':
            self.label[0].setText('Window length (sec)')
            self.label[1].setText('Window step (sec)')
            self.label[2].setText('Absolute power threshold')
            self.label[3].setText('Relative power threshold')
            self.label[4].setText('Covariance threshold')
            self.label[5].setText('Correlation threshold')
            
            self.index['0'].set_value(spin_det.windowing['dur'])
            self.index['1'].set_value(spin_det.windowing['step'])
            self.index['2'].set_value(spin_det.abs_pow_thresh)
            self.index['3'].set_value(spin_det.rel_pow_thresh)
            self.index['4'].set_value(spin_det.covar_thresh)
            self.index['5'].set_value(spin_det.corr_thresh)

        if self.method == 'FASST':
            self.label[0].setText('Detection threshold (percentile)')
            self.label[1].setText('Smoothing window length (sec)')
            self.label[2].setText('')
            self.label[3].setText('')
            self.label[4].setText('')
            self.label[5].setText('')

            self.index['0'].set_value(spin_det.det_thresh)
            self.index['1'].set_value(spin_det.smooth['dur'])
            
        if self.method == 'FASST2':
            self.label[0].setText('Detection threshold (percentile)')
            self.label[1].setText('RMS window length (sec)')
            self.label[2].setText('Smoothing window length (sec)')
            self.label[3].setText('')
            self.label[4].setText('')
            self.label[5].setText('')

            self.index['0'].set_value(spin_det.det_thresh)
            self.index['1'].set_value(spin_det.moving_rms['dur'])
            self.index['2'].set_value(spin_det.smooth['dur'])
            
        if 'UCSD' in self.method:
            self.label[0].setText('Wavelet duration (sec)')
            self.label[1].setText('Wavelet width (sec)')
            self.label[2].setText('Smoothing window length (sec)')
            self.label[3].setText('Detection threshold (SD)')
            self.label[4].setText('Selection threshold (SD)')
            self.label[5].setText('')

            self.index['0'].set_value(spin_det.det_wavelet['dur'])
            self.index['1'].set_value(spin_det.det_wavelet['width'])
            self.index['2'].set_value(spin_det.det_wavelet['win'])
            self.index['3'].set_value(spin_det.det_thresh)
            self.index['4'].set_value(spin_det.sel_thresh)

        if 'Concordia' in self.method:
            self.label[0].setText('RMS window length (sec)')
            self.label[1].setText('Smoothing window length (sec)')
            self.label[2].setText('Detection threshold, low (SD)')
            self.label[3].setText('Detection threshold, high (SD)')
            self.label[4].setText('Tolerance (sec)')
            self.label[5].setText('Selection threshold (SD)')

            self.index['0'].set_value(spin_det.moving_rms['dur'])
            self.index['1'].set_value(spin_det.smooth['dur'])
            self.index['2'].set_value(spin_det.det_thresh)
            self.index['3'].set_value(spin_det.det_thresh_hi)
            self.index['4'].set_value(spin_det.tolerance)
            self.index['5'].set_value(spin_det.sel_thresh)
        
        for i, j in enumerate(self.label):
            one_param = self.index[str(i)]
            if j.text() == '':
                one_param.set_value('')
                one_param.setEnabled(False)
            else:
                one_param.setEnabled(True)

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
    name, channel, stage, min dur, max dur, detection method, lowcut, highcut,
    minimum and maximum trough duration, maximum trough amplitude, minimum
    peak-to-peak amplitude.

    Attributes
    ----------
    name : str
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

        self.name = FormStr()

        self.name.setText('sw')
        self.idx_group.activated.connect(self.update_channels)

        form = QFormLayout(box0)
        form.addRow('Event name',
                           self.name)
        form.addRow('Channel group',
                       self.idx_group)
        form.addRow('Channel(s)',
                       self.idx_chan)
        form.addRow('Cycle(s)',
                       self.idx_cycle)
        form.addRow('Stage(s)',
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

        form = QFormLayout(box1)
        form.addRow('Method',
                            mbox)
        form.addRow('Lowcut (Hz)',
                           self.index['f1'])
        form.addRow('Highcut (Hz)',
                           self.index['f2'])
        form.addRow('Min. trough duration (sec)',
                           self.index['min_trough_dur'])
        form.addRow(' Max. trough duration (sec)',
                           self.index['max_trough_dur'])
        form.addRow(' Max. trough amplitude (uV)',
                           self.index['max_trough_amp'])
        form.addRow('Min. peak-to-peak amplitude (uV)',
                           self.index['min_ptp'])
        form.addRow('Min. duration (sec)',
                           self.index['min_dur'])
        form.addRow(' Max. duration (sec)',
                           self.index['max_dur'])
        box3 = QGroupBox('Options')

        self.index['detrend'] = FormBool('Detrend (linear)')
        self.index['invert'] = FormBool('Invert detection (down-then-up)')
        self.index['excl_epoch'] = FormBool('Exclude Poor signal epochs')
        self.index['excl_event'] = FormMenu(['none', 'channel-specific', 
                                      'from any channel'])
        self.index['min_seg_dur'] = FormFloat(5)

        self.index['excl_epoch'].set_value(True)
        self.index['detrend'].set_value(True)

        form = QFormLayout(box3)
        form.addRow(self.index['excl_epoch'])
        form.addRow('Exclude Artefact events', 
                    self.index['excl_event'])
        form.addRow('Minimum subsegment duration',
                       self.index['min_seg_dur'])
        form.addRow(self.index['detrend'])
        form.addRow(self.index['invert'])

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
            group = self.one_grp
            cycle = self.get_cycles()
            stage = self.idx_stage.selectedItems()
            params = {k: v.get_value() for k, v in self.index.items()}
            name = self.name.get_value()

            if None in [params['f1'], params['f2']]:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]

            chan_full = None
            reject_artf = False
            if params['excl_event'] == 'channel-specific':
                chan_full = [i + ' (' + self.idx_group.currentText() + ''
                           ')' for i in chans]
                chans = None
                reject_artf = True
            elif params['excl_event'] == 'from any channel':
                reject_artf = True
            
            data = fetch(self.parent.info.dataset, 
                                  self.parent.notes.annot, cat=(1, 1, 1, 0),
                                  stage=stage, cycle=cycle, 
                                  chan_full=chan_full,
                                  min_dur=params['min_seg_dur'], 
                                  reject_epoch=params['excl_epoch'], 
                                  reject_artf=reject_artf)
            
            if not data.segments:
                msg = 'No valid signal found.'
                error_dialog = QErrorMessage(self)
                error_dialog.setWindowTitle('Error fetching data')
                error_dialog.showMessage(msg)
                return
            
            ding = data.read_data(chans, group['ref_chan'], group['name'],
                                  parent=self)
            
            if not ding:
                self.parent.statusBar().showMessage('Process interrupted.')
                return

            data = data[0]['data']
            if params['detrend']:
                data = math(data, operator_name='detrend', axis='time')
            
            self.parent.notes.detect_events(data, self.method, 
                                            params, label=name)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

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
