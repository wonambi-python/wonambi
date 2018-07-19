""" Modal dialogs for carrying out automatic detections.
"""

from logging import getLogger

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QComboBox,
                             QErrorMessage,
                             QFormLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QVBoxLayout,
                             )

from ..detect import DetectSpindle, DetectSlowWave
from ..trans import fetch
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

        form = QFormLayout(box0)
        form.addRow('Label',
                       self.label)
        form.addRow('Channel group',
                       self.idx_group)
        form.addRow('Channel(s)',
                       self.idx_chan)
        form.addRow('Cycle(s)',
                       self.idx_cycle)
        form.addRow('Stage(s)',
                       self.idx_stage)

        box1 = QGroupBox('Parameters')

        self.index['f1'] = FormFloat()
        self.index['f2'] = FormFloat()
        self.index['rolloff'] = FormFloat()
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

        form = QFormLayout(box1)
        form.addRow('Method',
                       self.idx_method)
        form.addRow('Lowcut (Hz)',
                       self.index['f1'])
        form.addRow('Highcut (Hz)',
                       self.index['f2'])
        form.addRow('Roll-off (Hz)',
                       self.index['rolloff'])
        form.addRow('Min. duration (sec)',
                       self.index['min_dur'])
        form.addRow(' Max. duration (sec)',
                       self.index['max_dur'])
        form.addRow('Wavelet sigma',
                       self.index['sigma'])
        form.addRow('Detection window',
                       self.index['win_sz'])
        form.addRow('Smoothing',
                       self.index['smooth'])
        form.addRow('Detection threshold, low',
                       self.index['det_thresh_lo'])
        form.addRow('Detection threshold, high',
                       self.index['det_thresh_hi'])
        form.addRow('Selection threshold',
                       self.index['sel_thresh'])
        form.addRow('Min. interval',
                       self.index['interval'])

        box3 = QGroupBox('Options')

        self.index['merge'] = FormBool('Merge events across channels')
        self.index['excl_epoch'] = FormBool('Exclude Poor signal epochs')
        self.index['excl_event'] = FormBool('Exclude Artefact events')
        self.index['min_seg_dur'] = FormFloat(5)

        self.index['excl_epoch'].set_value(True)
        self.index['excl_event'].set_value(True)
        self.index['merge'].setCheckState(Qt.Unchecked)
        self.index['merge'].setEnabled(False)

        form = QFormLayout(box3)
        form.addRow(self.index['excl_epoch'])
        form.addRow(self.index['excl_event'])
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
            label = self.label.get_value()

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

            data = fetch(self.parent.info.dataset, 
                          self.parent.notes.annot, cat=(1, 1, 1, 0),
                          stage=stage, cycle=cycle, 
                          min_dur=params['min_seg_dur'], 
                          reject_epoch=params['excl_epoch'], 
                          reject_artf=params['excl_event'])
            
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
            
            self.parent.notes.detect_events(data[0]['data'], self.method, 
                                            params, label=label)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

    def update_values(self):
        """Update form values when detection method is selected."""
        self.method = self.idx_method.currentText()
        spin_det = DetectSpindle(method=self.method)

        if self.method in ['Wamsley2012', 'UCSD']:
            self.index['win_sz'].set_value(spin_det.det_wavelet['dur'])
        elif self.method == 'Ray2015':
            self.index['win_sz'].set_value(spin_det.zwin['dur'])
        else:
            self.index['win_sz'].set_value(spin_det.moving_rms['dur'])

        self.index['f1'].set_value(spin_det.frequency[0])
        self.index['f2'].set_value(spin_det.frequency[1])
        self.index['rolloff'].set_value(spin_det.rolloff)
        self.index['min_dur'].set_value(spin_det.duration[0])
        self.index['max_dur'].set_value(spin_det.duration[1])
        self.index['sigma'].set_value(spin_det.det_wavelet['sd'])
        self.index['smooth'].set_value(spin_det.smooth['dur'])
        self.index['det_thresh_lo'].set_value(spin_det.det_thresh_lo)
        self.index['det_thresh_hi'].set_value(spin_det.det_thresh_hi)
        self.index['sel_thresh'].set_value(spin_det.sel_thresh)
        self.index['interval'].set_value(spin_det.min_interval)

        for param in ['sigma', 'win_sz', 'det_thresh_lo', 'det_thresh_hi',
                      'sel_thresh', 'smooth', 'rolloff']:
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

        form = QFormLayout(box0)
        form.addRow('Label',
                           self.label)
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

        self.index['demean'] = FormBool('De-mean (by channel mean)')
        self.index['exclude'] = FormBool('Exclude Artefact events')
        self.index['invert'] = FormBool('Invert detection')
        self.index['excl_epoch'] = FormBool('Exclude Poor signal epochs')
        self.index['excl_event'] = FormBool('Exclude Artefact events')
        self.index['min_seg_dur'] = FormFloat(5)

        self.index['excl_epoch'].set_value(True)
        self.index['excl_event'].set_value(True)
        self.index['demean'].set_value(True)
        self.index['exclude'].set_value(True)

        form = QFormLayout(box3)
        form.addRow(self.index['excl_epoch'])
        form.addRow(self.index['excl_event'])
        form.addRow('Minimum subsegment duration',
                       self.index['min_seg_dur'])
        #form.addRow(self.index['demean'])
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
            label = self.label.get_value()

            if None in [params['f1'], params['f2']]:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]

            data = fetch(self.parent.info.dataset, 
                                  self.parent.notes.annot, cat=(1, 1, 1, 0),
                                  stage=stage, cycle=cycle, 
                                  min_dur=params['min_seg_dur'], 
                                  reject_epoch=params['excl_epoch'], 
                                  reject_artf=params['excl_event'])
            
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
            
            self.parent.notes.detect_events(data[0]['data'], self.method, 
                                            params, label=label)

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
