# -*- coding: utf-8 -*-

"""Dialogs for analyses, such as power spectra, PAC, event parameters
"""
from operator import itemgetter
from logging import getLogger
from numpy import (arange, asarray, concatenate, diff, empty, floor, in1d, inf,
                   log, logical_and, logical_or, mean, nan_to_num, ptp, ravel,
                   sqrt, square, std, zeros)
from math import isclose
from csv import writer
from os.path import basename, splitext
from pickle import dump, load
try:
    from tensorpac import Pac
    from tensorpac.pacstr import pacstr
except ImportError:
    Pac = pacstr = None

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (QAbstractItemView,
                             QDialogButtonBox,
                             QDoubleSpinBox,
                             QFileDialog,
                             QFormLayout,
                             QGridLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit,
                             QListWidget,
                             QMessageBox,
                             QPushButton,
                             QSpinBox,
                             QTabWidget,
                             QVBoxLayout,
                             QWidget,
                             )

from .. import ChanTime
from ..trans import montage, filter_, frequency
from .notes import ChannelDialog, STAGE_NAME
from .settings import (FormStr, FormInt, FormFloat, FormBool, FormMenu,
                       FormRadio)
from .utils import freq_from_str, short_strings, remove_artf_evts

lg = getLogger(__name__)

POWER_METHODS = ['Welch', 'Multitaper']

class AnalysisDialog(ChannelDialog):
    """Dialog for specifying various types of analyses: per event, per epoch or
    per entire segments of signal. PSD, PAC, event metrics. Option to transform
    signal before analysis. Creates a pickle object.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window
    group : dict
        information about groups from Channels
    """
    def __init__(self, parent):
        ChannelDialog.__init__(self, parent)

        self.setWindowTitle('Analysis')
        self.chunk = {}
        self.label = {}
        self.cat = {}
        self.trans = {}
        self.event_types = None
        self.event = {}
        self.psd = {}
        self.pac = {}

        self.create_dialog()

    def create_dialog(self):
        """Create the dialog."""
        bbox = QDialogButtonBox(QDialogButtonBox.Help | QDialogButtonBox.Ok |
                QDialogButtonBox.Cancel)
        self.idx_help = bbox.button(QDialogButtonBox.Help)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)

        """ ------ FILE LOCATION ------ """

        box_f = QGroupBox('File location')

        filebutton = QPushButton('Choose')
        #filebutton.setText('Choose')
        filebutton.clicked.connect(self.save_as)
        self.idx_filename = filebutton

        flayout = QFormLayout()
        box_f.setLayout(flayout)
        flayout.addRow('Filename',
                            self.idx_filename)

        """ ------ CHUNKING ------ """

        box0 = QGroupBox('Chunking')

        self.chunk['event'] = FormRadio('by e&vent')
        self.chunk['epoch'] = FormRadio('by e&poch')
        self.chunk['segment'] = FormRadio('by longest &segment')
        self.label['evt_type'] = QLabel('Event type (s)')
        self.label['epoch_dur'] = QLabel('Duration (sec)')
        self.label['min_dur'] = QLabel('Minimum duration (sec)')
        self.evt_chan_only = FormBool('Channel-specific')
        self.epoch_dur = FormFloat(30.0)
        self.lock_to_staging = FormBool('Lock to staging epochs')

        evt_box = QListWidget()
        evt_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_evt_type = evt_box

        grid = QGridLayout(box0)
        box0.setLayout(grid)
        grid.addWidget(self.chunk['event'], 0, 0, 1, 3)
        grid.addWidget(QLabel('    '), 1, 0)
        grid.addWidget(self.evt_chan_only, 1, 1, 1, 2)
        grid.addWidget(QLabel('    '), 2, 0)
        grid.addWidget(self.label['evt_type'], 2, 1, Qt.AlignTop)
        grid.addWidget(self.idx_evt_type, 2, 2, 1, 2)
        grid.addWidget(self.chunk['epoch'], 3, 0, 1, 3)
        grid.addWidget(QLabel('    '), 4, 0)
        grid.addWidget(self.lock_to_staging, 4, 1, 1, 2)
        grid.addWidget(QLabel('    '), 4, 0)
        grid.addWidget(self.label['epoch_dur'], 5, 1)
        grid.addWidget(self.epoch_dur, 5, 2)
        grid.addWidget(self.chunk['segment'], 6, 0, 1, 3)


        """ ------ LOCATION ------ """

        box1 = QGroupBox('Location')

#==============================================================================
#         cycle_box = QListWidget()
#         cycle_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
#         self.idx_cycle = cycle_box
#==============================================================================

        flayout = QFormLayout()
        box1.setLayout(flayout)
        flayout.addRow('Channel group',
                            self.idx_group)
        flayout.addRow('Channel(s)',
                            self.idx_chan)
        flayout.addRow('Cycle(s)',
                            self.idx_cycle)
        flayout.addRow('Stage(s)',
                            self.idx_stage)

        """ ------ REJECTION ------ """

        box_r = QGroupBox('Rejection')

        self.min_dur = FormFloat(0.0)
        self.reject_epoch = FormBool('Exclude Poor signal epochs')
        self.reject_event = FormBool('Exclude Artefact events')

        flayout = QFormLayout()
        box_r.setLayout(flayout)
        flayout.addRow('Minimum duration (sec)',
                           self.min_dur)
        flayout.addRow(self.reject_epoch)
        flayout.addRow(self.reject_event)

        """ ------ CONCATENATION ------ """

        box_c = QGroupBox('Concatenation')

        self.cat['chan'] = FormBool('Concatenate channels')
        self.cat['cycle'] = FormBool('Concatenate cycles')
        self.cat['stage'] = FormBool('Concatenate between stages')
        self.cat['discontinuous'] = FormBool(''
                'Concatenate discontinuous signal')
        self.cat['evt_type'] = FormBool('Concatenate between event types')

        for box in self.cat.values():
            box.setEnabled(False)

        flayout = QFormLayout()
        box_c.setLayout(flayout)
        flayout.addRow(self.cat['stage'])
        flayout.addRow(self.cat['cycle'])
        flayout.addRow(self.cat['evt_type'])
        flayout.addRow(self.cat['discontinuous'])
        flayout.addRow(self.cat['chan'])

        """ ------ PRE-PROCESSING ------ """

        box2 = QGroupBox('Pre-processing')

        self.trans['button'] = {}
        tb = self.trans['button']
        tb['none'] = FormRadio('&None')
        tb['butter'] = FormRadio('&Butterworth filter')
        tb['cheby'] = FormRadio('&Chebyshev filter')
        tb['bessel'] = FormRadio('Besse&l filter')

        self.trans['filt'] = {}
        filt = self.trans['filt']
        filt['order'] = QLabel('Order'), FormInt(default=3)
        filt['f1'] = QLabel('Lowcut (Hz)'), FormFloat()
        filt['f2'] = QLabel('Highcut (Hz)'), FormFloat()
        filt['notch_centre'] = QLabel('Centre (Hz)'), FormFloat()
        filt['notch_bandw'] = QLabel('Bandwidth (Hz)'), FormFloat()
        filt['bandpass_l'] = QLabel('Bandpass'), None
        filt['notch_l'] = QLabel('Notch'), None

        flayout = QFormLayout()
        box2.setLayout(flayout)
        flayout.addRow(tb['none'])
        flayout.addRow(tb['butter'])
        flayout.addRow(tb['cheby'])
        flayout.addRow(tb['bessel'])
        flayout.addRow(*filt['order'])
        flayout.addRow(filt['bandpass_l'][0])
        flayout.addRow(*filt['f1'])
        flayout.addRow(*filt['f2'])
        flayout.addRow(filt['notch_l'][0])
        flayout.addRow(*filt['notch_centre'])
        flayout.addRow(*filt['notch_bandw'])

        """ ------ FREQUENCY ------ """

        tab_freq = QWidget()

        self.frequency = {}
        freq = self.frequency

        freq['freq_on'] = FormBool('Compute frequency domain')

        freq['box_param'] = QGroupBox('Parameters')

        freq['scaling'] = FormMenu(['power', 'energy', 'fieldtrip', 'chronux'])
        freq['taper'] = FormMenu(['boxcar', 'hann', 'dpss', 'triang',
            'blackman', 'hamming', 'bartlett', 'flattop', 'parzen', 'bohman',
                'blackmanharris', 'nuttall', 'barthann'])
        freq['detrend'] = FormMenu(['none', 'constant', 'linear'])
        freq['welch_on'] = FormBool("Welch's method")

        flayout = QFormLayout(freq['box_param'])
        flayout.addRow('Scaling', freq['scaling'])
        flayout.addRow('Taper', freq['taper'])
        flayout.addRow('Detrend', freq['detrend'])
        flayout.addRow(freq['welch_on'])

        freq['box_welch'] = QGroupBox("Welch's method")

        freq['duration'] = FormFloat(1)
        freq['overlap'] = FormRadio('Overlap (0-1)')
        freq['step'] = FormRadio('Step (sec)')
        freq['overlap_val'] = QDoubleSpinBox()
        freq['overlap_val'].setRange(0, 1)
        freq['overlap_val'].setSingleStep(0.1)
        freq['overlap_val'].setValue(0.5)
        freq['step_val'] = FormFloat()

        glayout = QGridLayout(freq['box_welch'])
        glayout.addWidget(QLabel('Duration (sec)'), 0, 0)
        glayout.addWidget(freq['duration'], 0, 1)
        glayout.addWidget(freq['overlap'], 1, 0)
        glayout.addWidget(freq['step'], 2, 0)
        glayout.addWidget(freq['overlap_val'], 1, 1)
        glayout.addWidget(freq['step_val'], 2, 1)

        freq['box_mtap'] = QGroupBox('Multitaper method (DPSS) smoothing')

        freq['hbw'] = FormRadio('Half bandwidth (Hz)')
        freq['nhbw'] = FormRadio('Normalized \nhalf bandwidth')
        freq['hbw_val'] = QSpinBox()
        freq['hbw_val'].setMinimum(0)
        freq['hbw_val'].setValue(3)
        freq['nhbw_val'] = QSpinBox()
        freq['nhbw_val'].setMinimum(0)

        glayout = QGridLayout()
        freq['box_mtap'].setLayout(glayout)
        glayout.addWidget(freq['hbw'], 0, 0)
        glayout.addWidget(freq['nhbw'], 1, 0)
        glayout.addWidget(freq['hbw_val'], 0, 1)
        glayout.addWidget(freq['nhbw_val'], 1, 1)

        freq['box_output'] = QGroupBox('Output')

        freq['spectrald'] = FormRadio('Spectral density')
        freq['complex'] = FormRadio('Complex')
        freq['sides'] = QSpinBox()
        freq['sides'].setRange(1,2)
        freq['sides'].setValue(1)

        glayout = QGridLayout(freq['box_output'])
        glayout.addWidget(freq['spectrald'], 0, 0, 1, 3)
        glayout.addWidget(freq['complex'], 1, 0, 1, 3)
        glayout.addWidget(QLabel('      '), 2, 0)
        glayout.addWidget(QLabel('Side(s)'), 2, 1)
        glayout.addWidget(freq['sides'], 2, 2)

        freq['box_norm'] = QGroupBox('Normalization')

        freq['norm'] = FormMenu(['none', 'by mean of each segment',
           'by mean of event type(s)', 'by mean of stage(s)',
            'by mean of recording'])
        evt_box = QListWidget()
        evt_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        freq['norm_evt_type'] = evt_box
        stage_box = QListWidget()
        stage_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        stage_box.addItems(STAGE_NAME)
        freq['norm_stage'] = stage_box
        freq['norm_concat'] = FormBool('Concatenate')

        glayout = QGridLayout(freq['box_norm'])
        glayout.addWidget(freq['norm'], 0, 0, 1, 2)
        glayout.addWidget(QLabel('Event type(s)'), 1, 0)
        glayout.addWidget(QLabel('Stage(s)'), 1, 1)
        glayout.addWidget(freq['norm_evt_type'], 2, 0)
        glayout.addWidget(freq['norm_stage'], 2, 1)
        glayout.addWidget(freq['norm_concat'], 3, 0, 1, 2)

        glayout = QGridLayout()
        glayout.addWidget(freq['box_param'], 0, 0)
        glayout.addWidget(freq['box_output'], 1, 0)
        glayout.addWidget(freq['box_welch'], 0, 1)
        glayout.addWidget(freq['box_mtap'], 1, 1)
        glayout.addWidget(freq['box_norm'], 2, 0)

        vlayout = QVBoxLayout(tab_freq)
        vlayout.addWidget(freq['freq_on'])
        vlayout.addLayout(glayout)
        #vlayout.addWidget(freq['box_norm'])
        vlayout.addStretch(1)

        """ ------ PAC ------ """
        if Pac is not None:

            tab_pac = QWidget()

            pac_metrics = [pacstr((x, 0, 0))[0] for x in range(1,6)]
            pac_metrics = [x[:x.index('(') - 1] for x in pac_metrics]
            pac_metrics[1] = 'Kullback-Leibler Distance' # corrected typo
            pac_surro = [pacstr((1, x, 0))[1] for x in range(5)]
            pac_norm = [pacstr((1, 0, x))[2] for x in range(5)]

            pac = self.pac

            pac['box_complex'] = QGroupBox('Complex definition')

            pac['hilbert_on'] = FormRadio('Hilbert transform')
            pac['hilbert'] = {}
            hilb = pac['hilbert']
            hilb['filt'] = QLabel('Filter'), FormMenu(['fir1', 'butter',
                'bessel'])
            hilb['cycle_pha'] = QLabel('Cycles, phase'), FormInt(default=3)
            hilb['cycle_amp'] = QLabel('Cycles, amp'), FormInt(default=6)
            hilb['order'] = QLabel('Order'), FormInt(default=3)
            pac['wavelet_on'] = FormRadio('Wavelet convolution')
            pac['wav_width'] = QLabel('Width'), FormInt(default=7)

            grid = QGridLayout(pac['box_complex'])
            grid.addWidget(pac['hilbert_on'], 0, 0, 1, 2)
            grid.addWidget(hilb['filt'][0], 1, 0)
            grid.addWidget(hilb['filt'][1], 1, 1)
            grid.addWidget(hilb['cycle_pha'][0], 2, 0)
            grid.addWidget(hilb['cycle_pha'][1], 2, 1)
            grid.addWidget(hilb['cycle_amp'][0], 3, 0)
            grid.addWidget(hilb['cycle_amp'][1], 3, 1)
            grid.addWidget(hilb['order'][0], 4, 0)
            grid.addWidget(hilb['order'][1], 4, 1)
            grid.addWidget(pac['wavelet_on'], 0, 3, 1, 2)
            grid.addWidget(pac['wav_width'][0], 1, 3)
            grid.addWidget(pac['wav_width'][1], 1, 4)

            pac['box_metric'] = QGroupBox('PAC metric')

            pac['pac_on'] = FormBool('Compute PAC')
            pac['metric'] = FormMenu(pac_metrics)
            pac['fpha'] = FormStr()
            pac['famp'] = FormStr()
            pac['nbin'] = QLabel('Number of bins'), FormInt(default=18)

            flayout = QFormLayout(pac['box_metric'])
            flayout.addRow(pac['pac_on'])
            flayout.addRow('PAC metric',
                               pac['metric'])
            flayout.addRow('Phase frequencies (Hz)',
                               pac['fpha'])
            flayout.addRow('Amplitude frequencies (Hz)',
                               pac['famp'])
            flayout.addRow(*pac['nbin'])

            pac['box_surro'] = QGroupBox('Surrogate data')

            pac['surro_method'] = FormMenu(pac_surro)
            pac['surro'] = {}
            sur = pac['surro']
            sur['nperm'] = QLabel('Number of surrogates'), FormInt(default=200)
            sur['nblocks'] = (QLabel('Number of amplitude blocks'),
                              FormInt(default=2))
            sur['pval'] = FormBool('Get p-values'), None
            sur['save_surro'] = FormBool('Save surrogate data'), None
            sur['norm'] = FormMenu(pac_norm), None

            flayout = QFormLayout(pac['box_surro'])
            flayout.addRow(pac['surro_method'])
            flayout.addRow(*sur['nperm'])
            flayout.addRow(*sur['nblocks'])
            flayout.addRow(sur['pval'][0])
            flayout.addRow(sur['save_surro'][0])
            flayout.addRow(sur['norm'][0])

            pac['box_opts'] = QGroupBox('Options')

            pac['optimize'] = FormMenu(['True', 'False', 'greedy', 'optimal'])
            pac['njobs'] = FormInt(default=-1)

            flayout = QFormLayout(pac['box_opts'])
            flayout.addRow('Optimize einsum',
                               pac['optimize'])
            flayout.addRow('Number of jobs',
                               pac['njobs'])

            vlayout = QVBoxLayout(tab_pac)
            vlayout.addWidget(pac['pac_on'])
            vlayout.addWidget(QLabel(''))
            vlayout.addWidget(pac['box_metric'])
            vlayout.addWidget(pac['box_complex'])
            vlayout.addWidget(pac['box_surro'])
            vlayout.addWidget(pac['box_opts'])

        """ ------ EVENTS ------ """

        tab_evt = QWidget()

        ev = self.event
        ev['global'] = {}
        eg = ev['global']
        eg['count'] = FormBool('Count')
        eg['density'] = FormBool('Density, per (sec)')
        eg['density_per'] = FormFloat(default=30.0)
        eg['all_local'] = FormBool('All')
        eg['all_local_prep'] = FormBool('')

        ev['local'] = {}
        el = ev['local']
        el['dur'] = FormBool('Duration (sec)'), FormBool('')
        el['minamp'] = FormBool('Minimum amplitude (uV)'), FormBool('')
        el['maxamp'] = FormBool('Maximum amplitude (uV)'), FormBool('')
        el['ptp'] = FormBool('Peak-to-peak amplitude (uV)'), FormBool('')
        el['rms'] = FormBool('RMS (uV)'), FormBool('')
        el['avg_power'] = FormBool('Average power (uV^2)'), FormBool('')
        el['auc'] = FormBool('Area under the curve (uV^2)'), FormBool('')
        el['peakf'] = FormBool('Peak frequency (Hz)'), FormBool('')

        ev['sw'] = {}
        ev['sw']['prep'] = FormBool('Pre-process')
        ev['sw']['all_slope'] = FormBool('All slopes')
        ev['slope'] = []
        for i in range(10):
            ev['slope'].append(FormBool(''))

        box_global = QGroupBox('Global')

        grid1 = QGridLayout(box_global)
        grid1.addWidget(eg['count'], 0, 0)
        grid1.addWidget(eg['density'], 1, 0)
        grid1.addWidget(eg['density_per'], 1, 1)

        box_local = QGroupBox('Local')

        grid2 = QGridLayout(box_local)
        grid2.addWidget(QLabel('Parameter'), 0, 0)
        grid2.addWidget(QLabel('  '), 0, 1)
        grid2.addWidget(QLabel('Pre-process'), 0, 2)
        grid2.addWidget(eg['all_local'], 1, 0)
        grid2.addWidget(eg['all_local_prep'], 1, 2)
        grid2.addWidget(el['dur'][0], 2, 0)
        grid2.addWidget(el['minamp'][0], 3, 0)
        grid2.addWidget(el['minamp'][1], 3, 2)
        grid2.addWidget(el['maxamp'][0], 4, 0)
        grid2.addWidget(el['maxamp'][1], 4, 2)
        grid2.addWidget(el['ptp'][0], 5, 0)
        grid2.addWidget(el['ptp'][1], 5, 2)
        grid2.addWidget(el['rms'][0], 6, 0)
        grid2.addWidget(el['rms'][1], 6, 2)
        grid2.addWidget(el['avg_power'][0], 7, 0)
        grid2.addWidget(el['avg_power'][1], 7, 2)
        grid2.addWidget(el['auc'][0], 8, 0)
        grid2.addWidget(el['auc'][1], 8, 2)
        grid2.addWidget(el['peakf'][0], 9, 0)
        grid2.addWidget(el['peakf'][1], 9, 2)

        box_sw = QGroupBox('Slow wave')

        grid3 = QGridLayout(box_sw)
        grid3.addWidget(ev['sw']['prep'], 0, 0, 1, 2)
        grid3.addWidget(ev['sw']['all_slope'], 1, 0, 1, 2)
        grid3.addWidget(QLabel('Quadrant'), 2, 0)
        grid3.addWidget(QLabel('Average\nslope (uV/s)'), 2, 1)
        grid3.addWidget(QLabel('Maximum\nslope (uV/s)'), 2, 2)
        grid3.addWidget(QLabel('1'), 3, 0)
        grid3.addWidget(QLabel('2'), 4, 0)
        grid3.addWidget(QLabel('3'), 5, 0)
        grid3.addWidget(QLabel('4'), 6, 0)
        grid3.addWidget(QLabel('2 & 3'), 7, 0)
        for i,w in enumerate(ev['slope']):
            x = floor(i/5)
            grid3.addWidget(w, i - 5 * x + 3, x + 1)

        vlayout = QVBoxLayout(tab_evt)
        vlayout.addWidget(box_global)
        vlayout.addWidget(box_local)
        vlayout.addWidget(box_sw)
        vlayout.addStretch(1)

        """ ------ TRIGGERS ------ """

        for button in self.chunk.values():
            button.toggled.connect(self.toggle_buttons)

        for lw in [self.idx_chan, self.idx_cycle, self.idx_stage,
                   self.idx_evt_type]:
            lw.itemSelectionChanged.connect(self.toggle_concatenate)

        for button in self.trans['button'].values():
            button.toggled.connect(self.toggle_buttons)

        for button in [x[0] for x in self.event['local'].values()]:
            button.connect(self.toggle_buttons)

        self.chunk['epoch'].toggled.connect(self.toggle_concatenate)
        self.chunk['event'].toggled.connect(self.toggle_concatenate)
        self.idx_group.activated.connect(self.update_channels)
        self.lock_to_staging.connect(self.toggle_buttons)
        self.cat['discontinuous'].connect(self.toggle_concatenate)

        freq['freq_on'].connect(self.toggle_freq)
        freq['taper'].connect(self.toggle_freq)
        freq['welch_on'].connect(self.toggle_freq)
        freq['complex'].connect(self.toggle_freq)
        freq['overlap'].connect(self.toggle_freq)
        freq['hbw'].connect(self.toggle_freq)
        freq['norm'].connect(self.toggle_freq)

        if Pac is not None:
            pac['pac_on'].connect(self.toggle_pac)
            pac['hilbert_on'].toggled.connect(self.toggle_pac)
            pac['wavelet_on'].toggled.connect(self.toggle_pac)
            pac['metric'].connect(self.toggle_pac)
            pac['surro_method'].connect(self.toggle_pac)

        eg['density'].connect(self.toggle_buttons)
        eg['all_local'].clicked.connect(self.check_all_local)
        eg['all_local_prep'].clicked.connect(self.check_all_local_prep)
        for button in el.values():
            button[0].clicked.connect(self.uncheck_all_local)
            button[1].clicked.connect(self.uncheck_all_local)
        ev['sw']['all_slope'].connect(self.check_all_slopes)

        bbox.clicked.connect(self.button_clicked)

        """ ------ SET DEFAULTS ------ """

        self.evt_chan_only.setChecked(True)
        self.lock_to_staging.setChecked(True)
        self.chunk['epoch'].setChecked(True)
        self.reject_epoch.setChecked(True)
        self.trans['button']['none'].setChecked(True)

        freq['box_param'].setEnabled(False)
        freq['box_welch'].setEnabled(False)
        freq['box_mtap'].setEnabled(False)
        freq['box_output'].setEnabled(False)
        freq['box_norm'].setEnabled(False)
        freq['spectrald'].setChecked(True)
        freq['detrend'].set_value('linear')
        freq['overlap'].setChecked(True)
        freq['hbw'].setChecked(True)

        # TODO: remove this
        freq['norm'].setEnabled(False) # Temp

        if Pac is not None:
            pac['wavelet_on'].setChecked(True)
            pac['metric'].set_value('Kullback-Leibler Distance')
            pac['optimize'].set_value('False')
            pac['box_metric'].setEnabled(False)
            pac['box_complex'].setEnabled(False)
            pac['box_surro'].setEnabled(False)
            pac['box_opts'].setEnabled(False)

        el['dur'][1].set_value(False)

        """ ------ LAYOUT MASTER ------ """

        box3 = QTabWidget()

        box3.addTab(tab_freq, 'Frequency')
        if Pac is not None:
            box3.addTab(tab_pac, 'PAC')
        box3.addTab(tab_evt, 'Events')

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout1 = QVBoxLayout()
        vlayout1.addWidget(box_f)
        vlayout1.addWidget(box0)
        vlayout1.addWidget(box1)
        vlayout1.addStretch(1)

        vlayout2 = QVBoxLayout()
        vlayout2.addWidget(box_r)
        vlayout2.addWidget(box_c)
        vlayout2.addWidget(box2)
        vlayout2.addStretch(1)

        vlayout3 = QVBoxLayout()
        vlayout3.addWidget(box3)
        vlayout3.addStretch(1)
        vlayout3.addLayout(btnlayout)

        hlayout = QHBoxLayout()
        hlayout.addLayout(vlayout1)
        hlayout.addLayout(vlayout2)
        hlayout.addLayout(vlayout3)
        hlayout.addStretch(1)

        self.setLayout(hlayout)

    def update_evt_types(self):
        """Update the event types list when dialog is opened."""
        self.event_types = self.parent.notes.annot.event_types
        self.idx_evt_type.clear()
        self.frequency['norm_evt_type'].clear()
        for ev in self.event_types:
            self.idx_evt_type.addItem(ev)
            self.frequency['norm_evt_type'].addItem(ev)

    def toggle_buttons(self):
        """Enable and disable buttons, according to options selected."""
        event_on = self.chunk['event'].isChecked()
        epoch_on = self.chunk['epoch'].isChecked()
        segment_on = self.chunk['segment'].isChecked()
        lock_on = self.lock_to_staging.get_value()
        lock_enabled = self.lock_to_staging.isEnabled()

        self.evt_chan_only.setEnabled(event_on)
        self.label['evt_type'].setEnabled(event_on)
        self.idx_evt_type.setEnabled(event_on)
        self.label['epoch_dur'].setEnabled(epoch_on)
        self.epoch_dur.setEnabled(epoch_on)
        self.lock_to_staging.setEnabled(epoch_on)
        self.reject_epoch.setEnabled(not event_on)
        self.reject_event.setEnabled(logical_or((lock_enabled and not lock_on),
                                                not lock_enabled))
        self.cat['discontinuous'].setEnabled(event_on or segment_on)
        self.cat['evt_type'].setEnabled(event_on)

        if Pac is not None:
            self.pac['surro_method'].model().item(1).setEnabled(epoch_on)
        # "Swap phase/amplitude across trials" only available if using epochs
        # because trials need to be of equal length

        if event_on:
            self.reject_epoch.setChecked(False)
        elif self.cat['evt_type'].get_value():
            self.cat['evt_type'].setChecked(False)

        if epoch_on and lock_on:
            self.reject_event.setChecked(False)

        if epoch_on:
            for i in self.cat.values():
                i.setChecked(False)
                i.setEnabled(False)

        filter_on = not self.trans['button']['none'].isChecked()
        for button in self.trans['filt'].values():
            button[0].setEnabled(filter_on)
            if button[1] is not None:
                button[1].setEnabled(filter_on)

        density_on = self.event['global']['density'].isChecked()
        self.event['global']['density_per'].setEnabled(density_on)

        for buttons in self.event['local'].values():
            checked = buttons[0].isChecked()
            buttons[1].setEnabled(checked)
            if not checked:
                buttons[1].setChecked(False)

    def toggle_concatenate(self):
        """Enable and disable concatenation options."""
        if not self.chunk['epoch'].isChecked():
            for i,j in zip([self.idx_chan, self.idx_cycle, self.idx_stage,
                            self.idx_evt_type],
                   [self.cat['chan'], self.cat['cycle'],
                    self.cat['stage'], self.cat['evt_type']]):
                if len(i.selectedItems()) > 1:
                    j.setEnabled(True)
                else:
                    j.setEnabled(False)
                    j.setChecked(False)

        if not self.chunk['event'].isChecked():
            self.cat['evt_type'].setEnabled(False)

        if not self.cat['discontinuous'].get_value():
            self.cat['chan'].setEnabled(False)

    def toggle_freq(self):
        """Enable and disable frequency domain options."""
        freq = self.frequency

        freq_on = freq['freq_on'].get_value()
        freq['box_param'].setEnabled(freq_on)
        freq['box_output'].setEnabled(freq_on)
        freq['box_norm'].setEnabled(freq_on)

        welch_on = freq['welch_on'].get_value()
        freq['box_welch'].setEnabled(welch_on)

        if welch_on:
            overlap_on = freq['overlap'].isChecked()
            freq['overlap_val'].setEnabled(overlap_on)
            freq['step_val'].setEnabled(not overlap_on)

        dpss_on = freq['taper'].get_value() == 'dpss'
        freq['box_mtap'].setEnabled(dpss_on)

        if dpss_on:
            hbw_on = freq['hbw'].isChecked()
            freq['hbw_val'].setEnabled(hbw_on)
            freq['nhbw_val'].setEnabled(not hbw_on)

        complex_on = freq['complex'].isChecked()
        freq['sides'].setEnabled(complex_on)

        norm_evt = freq['norm'].get_value() == 'by mean of event type(s)'
        norm_stage = freq['norm'].get_value() == 'by mean of stage(s)'
        freq['norm_evt_type'].setEnabled(norm_evt)
        freq['norm_stage'].setEnabled(norm_stage)
        freq['norm_concat'].setEnabled(norm_evt or norm_stage)

    def toggle_pac(self):
        """Enable and disable PAC options."""
        if Pac is not None:
            pac_on = self.pac['pac_on'].get_value()
            self.pac['box_metric'].setEnabled(pac_on)
            self.pac['box_complex'].setEnabled(pac_on)
            self.pac['box_surro'].setEnabled(pac_on)
            self.pac['box_opts'].setEnabled(pac_on)

        if Pac is not None and pac_on:

            hilb_on = self.pac['hilbert_on'].isChecked()
            wav_on = self.pac['wavelet_on'].isChecked()
            for button in self.pac['hilbert'].values():
                button[0].setEnabled(hilb_on)
                if button[1] is not None:
                    button[1].setEnabled(hilb_on)
            self.pac['wav_width'][0].setEnabled(wav_on)
            self.pac['wav_width'][1].setEnabled(wav_on)

            if self.pac['metric'].get_value() in [
                    'Kullback-Leibler Distance',
                    'Heights ratio']:
                self.pac['nbin'][0].setEnabled(True)
                self.pac['nbin'][1].setEnabled(True)
            else:
                self.pac['nbin'][0].setEnabled(False)
                self.pac['nbin'][1].setEnabled(False)

            if self.pac['metric'] == 'ndPac':
                for button in self.pac['surro'].values():
                    button[0].setEnabled(False)
                    if button[1] is not None:
                        button[1].setEnabled(False)
                self.pac['surro']['pval'].setEnabled(True)

            ndpac_on = self.pac['metric'].get_value() == 'ndPac'
            surro_on = logical_and(self.pac['surro_method'].get_value() != ''
                                   'No surrogates', not ndpac_on)
            blocks_on = self.pac['surro_method'].get_value() == ''
            'Swap amplitude blocks across time'
            self.pac['surro_method'].setEnabled(not ndpac_on)
            for button in self.pac['surro'].values():
                button[0].setEnabled(surro_on)
                if button[1] is not None:
                    button[1].setEnabled(surro_on)
            self.pac['surro']['nblocks'][0].setEnabled(blocks_on)
            self.pac['surro']['nblocks'][1].setEnabled(blocks_on)
            if ndpac_on:
                self.pac['surro_method'].set_value('No surrogates')
                self.pac['surro']['pval'].setEnabled(True)

    def check_all_local(self):
        """Check or uncheck all local event parameters."""
        all_local_chk = self.event['global']['all_local'].isChecked()
        for buttons in self.event['local'].values():
            buttons[0].setChecked(all_local_chk)
            buttons[1].setEnabled(buttons[0].isChecked())

    def check_all_local_prep(self):
        """Check or uncheck all enabled event pre-processing."""
        all_local_pp_chk = self.event['global']['all_local_prep'].isChecked()
        for buttons in self.event['local'].values():
            if buttons[1].isEnabled():
                buttons[1].setChecked(all_local_pp_chk)

    def uncheck_all_local(self):
        """Uncheck 'all local' box when a local event is unchecked."""
        for buttons in self.event['local'].values():
            if not buttons[0].get_value():
                self.event['global']['all_local'].setChecked(False)
            if buttons[1].isEnabled() and not buttons[1].get_value():
                self.event['global']['all_local_prep'].setChecked(False)

    def check_all_slopes(self):
        """Check and uncheck slope options"""
        slopes_checked = self.event['sw']['all_slope'].get_value()
        for button in self.event['slope']:
            button.setChecked(slopes_checked)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            filename = self.filename
            if filename is None:
                return

            chunk = {k: v.isChecked() for k, v in self.chunk.items()}

            if chunk['event']:
                evt_type = self.idx_evt_type.selectedItems()
                if not evt_type:
                    return
                else:
                    evt_type = [x.text() for x in evt_type]
            else:
                evt_type = None

            # Which channel(s)
            group = self.one_grp
            chan = self.get_channels()
            if not chan:
                return
            chan_full = [i + ' (' + self.idx_group.currentText() + ''
                           ')' for i in chan]

            # Which cycle(s)
            cycle = self.get_cycles()

            # Which stage(s)
            stage = self.idx_stage.selectedItems()
            if not stage:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]
            lg.info('Stages from GUI: ' + str(stage))

            # Concatenation
            cat = {k: v.get_value() for k, v in self.cat.items()}
            lg.info('Cat: ' + str(cat))
            cat_chan = cat['chan']
            cat = (int(cat['cycle']), int(cat['stage']),
                   int(cat['discontinuous']), int(cat['evt_type']))

            # Other options
            lock_to_staging = self.lock_to_staging.get_value()
            exclude_epoch = self.reject_epoch.get_value()
            evt_chan_only = self.evt_chan_only.get_value()
            trans = {k: v.get_value() for k, v in self.trans['button'].items()}
            filt = {k: v[1].get_value() for k, v in \
                    self.trans['filt'].items() if v[1] is not None}

            # Event parameters
            ev_glo = {k: v.get_value() for k, v in \
                      self.event['global'].items()}
            ev_loc = {k: v[0].get_value() for k, v in \
                      self.event['local'].items()}
            ev_loc_prep = {k: v[1].get_value() for k, v in \
                           self.event['local'].items()}
            ev_sw = {k: v.get_value() for k, v in self.event['sw'].items()}
            ev_sl = [x.get_value() for x in self.event['slope']]

            # Fetch signal
            lg.info('Getting ' + ', '.join((str(evt_type), str(stage),
                                           str(cycle), str(chan_full),
                                           str(exclude_epoch))))
            bundles = get_times(self.parent.notes.annot, evt_type=evt_type,
                                stage=stage, cycle=cycle, chan=chan_full,
                                exclude=exclude_epoch)
            lg.info('Get times: ' + str(len(bundles)))

            if not bundles:
                self.parent.statusBar().showMessage('No valid signal found.')
                self.accept()
                return

            if self.reject_event.get_value():
                for bund in bundles:
                    bund['times'] = remove_artf_evts(bund['times'],
                                                    self.parent.notes.annot,
                                                    min_dur=0)
            lg.info('After remove artf evts: ' + str(len(bundles)))

            if not bundles:
                self.parent.statusBar().showMessage('No valid signal found.')
                self.accept
                return

            lg.info('Preparing concatenation: ' + str(cat))
            bundles = concat(bundles, cat)
            lg.info('After concat: ' + str(len(bundles)))

            if chunk['epoch']:
                cat = (0, 0, 0, 0)

                if lock_to_staging:
                    bundles = divide_bundles(bundles)
                    lg.info('Divided ' + str(len(bundles)))

                else:
                    bundles = find_intervals(bundles,
                                             self.epoch_dur.get_value())
                    lg.info('Find intervals: ' + str(len(bundles)))

            segments = longer_than(bundles, self.min_dur.get_value())
            lg.info('Longer than: ' + str(len(segments)))

            if not segments:
                self.parent.statusBar().showMessage('No valid signal found.')
                self.accept
                return

            self.read_data(chan, group, segments, concat_chan=cat_chan,
                           evt_chan_only=evt_chan_only)
            lg.info('Created data, n_seg: ' + str(len(self.segments)))

            # Transform signal

            # Apply analyses and save

            if self.frequency['freq_on'].get_value():
                freq_filename = splitext(filename)[0] + '_freq.p'
                xfreq = self.compute_freq()

                with open(freq_filename, 'wb') as f:
                    dump(xfreq, f)

                self.export_freq(xfreq)

            if self.pac['pac_on'].get_value():
                xpac, fpha, famp = self.compute_pac()
                pac_filename = splitext(filename)[0] + '_pac.p'

                with open(pac_filename, 'wb') as f:
                    dump(xpac, f)

                self.export_pac(xpac, fpha, famp)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

    def save_as(self):
        """Dialog for getting name, location of data export file."""
        filename = splitext(
                self.parent.notes.annot.xml_file)[0] + '_data'
        filename, _ = QFileDialog.getSaveFileName(self, 'Export analysis data',
                                                  filename,
                                                  'Pickle (*.p)')
        if filename == '':
            return

        self.filename = filename
        short_filename = short_strings(basename(self.filename))
        self.idx_filename.setText(short_filename)

    def read_data(self, chan, group, segments, concat_chan, evt_chan_only):
        """Read data for analysis."""
        dataset = self.parent.info.dataset
        #chan = self.get_channels() # already given as an argument!
        chan_to_read = chan + self.one_grp['ref_chan']

        data = dataset.read_data(chan=chan_to_read)

        max_s_freq = self.parent.value('max_s_freq')
        if data.s_freq > max_s_freq:
            q = int(data.s_freq / max_s_freq)
            lg.debug('Decimate (no low-pass filter) at ' + str(q))

            data.data[0] = data.data[0][:, slice(None, None, q)]
            data.axis['time'][0] = data.axis['time'][0][slice(None, None, q)]
            data.s_freq = int(data.s_freq / q)

        lg.info('Sending segments for _create, nseg: ' + str(len(segments)))

        self.segments = _create_data_to_analyze(data, chan, self.one_grp,
                                                segments=segments,
                                                concat_chan=concat_chan,
                                                evt_chan_only=evt_chan_only)

#==============================================================================
#         self.chan = []
#         for ch in chan:
#             chan_grp_name = ch + ' (' + self.one_grp['name'] + ')'
#             self.chan.append(chan_grp_name)
#==============================================================================

    def compute_freq(self):
        """Compute frequency domain analysis.

        Returns
        -------
        list of dict
            each item is a dict where 'data' is an instance of ChanFreq for a
            single segment of signal, 'name' is the event type, if applicable,
            'times' is a tuple of the start and end times in sec, 'duration' is
            the actual duration of the segment, in seconds (can be dissociated
            from 'times' if the signal was concatenated)
            and with 'chan' (str), 'stage' (str) and 'cycle' (int)
        """
        freq = self.frequency
        scaling = freq['scaling'].get_value()
        sides = freq['sides'].value()
        taper = freq['taper'].get_value()
        halfbandwidth = freq['hbw_val'].value()
        NW = freq['nhbw_val'].value()
        duration = freq['duration'].get_value()
        overlap = freq['overlap_val'].value()
        step = freq['step_val'].get_value()
        detrend = freq['detrend'].get_value()

        if freq['spectrald'].isChecked():
            output = 'spectraldensity'
        else:
            output = 'complex'

        if sides == 1:
            sides = 'one'
        elif sides == 2:
            sides = 'two'

        if freq['overlap'].isChecked():
            step = None
        else:
            overlap = None

        if NW == 0 or freq['hbw'].isChecked():
            NW = None
        if duration == 0 or not freq['welch_on'].get_value():
            duration = None
        if step == 0:
            step = None
        if detrend == 'none':
            detrend = None

        lg.info(' '.join(['Freq settings:', output, scaling, 'sides:',
                         str(sides), taper, 'hbw:', str(halfbandwidth), 'NW:',
                         str(NW), 'dur:', str(duration), 'overlap:',
                         str(overlap), 'step:', str(step), 'detrend:',
                         str(detrend)]))

        xfreq = []
        for seg in self.segments:
            data = seg['data']
            timeline = seg['data'].axis['time'][0]
            seg['times'] = timeline[0], timeline[-1]
            seg['duration'] = len(timeline) / data.s_freq

            lg.info('Compute freq ' + ' ' + str((timeline[0], timeline[-1])))
            Sxx = frequency(data, output=output, scaling=scaling, sides=sides,
                            taper=taper, halfbandwidth=halfbandwidth, NW=NW,
                            duration=duration, overlap=overlap, step=step,
                            detrend=detrend)
            seg['data'] = Sxx
            xfreq.append(seg)

        return xfreq

    def compute_pac(self):
        """Compute phase-amplitude coupling values from data."""
        pac = self.pac
        idpac = (pac['metric'].currentIndex() + 1,
                 pac['surro_method'].currentIndex(),
                 pac['surro']['norm'][0].currentIndex())
        fpha = freq_from_str(self.pac['fpha'].get_value())
        famp = freq_from_str(self.pac['famp'].get_value())
        nbins = self.pac['nbin'][1].get_value()
        nblocks = self.pac['surro']['nblocks'][1].get_value()

        if pac['hilbert_on'].isChecked():
            dcomplex = 'hilbert'
            filt = self.pac['hilbert']['filt'][1].get_value()
            cycle = (self.pac['hilbert']['cycle_pha'][1].get_value(),
                     self.pac['hilbert']['cycle_amp'][1].get_value())
            filtorder = self.pac['hilbert']['order'][1].get_value()
            width = 7 # not used
        elif pac['wavelet_on'].isChecked():
            dcomplex = 'wavelet'
            filt = 'fir1' # not used
            cycle = (3, 6) # not used
            filtorder = 3 # not used
            width = self.pac['wav_width'][1].get_value()

        p = Pac(idpac=idpac, fpha=fpha, famp=famp, dcomplex=dcomplex,
                filt=filt, cycle=cycle, filtorder=filtorder, width=width,
                nbins=nbins, nblocks=nblocks)

        nperm = self.pac['surro']['nperm'][1].get_value()
        optimize = self.pac['optimize'].get_value()
        get_pval = self.pac['surro']['pval'][0].get_value()
        get_surro = self.pac['surro']['save_surro'][0].get_value()
        njobs = self.pac['njobs'].get_value()

        if optimize == 'True':
            optimize = True
        elif optimize == 'False':
            optimize = False

        xpac = {}

        all_chan = sorted(set(
                [x for y in self.segments for x in y['data'].axis['chan'][0]]))
        lg.info('all_chan: ' + str(all_chan))

        for chan in all_chan:
            lg.info('compute_pac: looping: ' + str(chan))
            batch = []
            batch_dat = []

            for i, j in enumerate(self.segments):

                if chan in j['data'].axis['chan'][0]:
                    batch.append(j)
                    lg.info('appending to batch segment with ' + str(j['data'].axis['chan'][0]))

                    if idpac[1] == 1:
                        batch_dat.append(j['data'](chan=chan)[0])

            xpac[chan] = {}
            xpac[chan]['data'] = zeros((len(batch), len(famp), len(fpha)))
            xpac[chan]['times'] = []
            xpac[chan]['duration'] = []
            xpac[chan]['stage'] = []
            xpac[chan]['cycle'] = []
            xpac[chan]['name'] = []

            if get_pval:
                xpac[chan]['pval'] = zeros((len(batch), len(famp), len(fpha)))

            if idpac[2] > 0:
                xpac[chan]['surro'] = zeros((len(batch), nperm,
                                            len(famp), len(fpha)))

            for i, j in enumerate(batch):
                sf = j['data'].s_freq

                if idpac[1] == 1:
                    new_batch_dat = list(batch_dat)
                    new_batch_dat.insert(0, new_batch_dat.pop(i))
                    dat = asarray(new_batch_dat)
                else:
                    lg.info('seeking ' + chan + ' in ' + str(j['data'].axis['chan'][0]))
                    dat = j['data'](chan=chan)[0]

                timeline = j['data'].axis['time'][0]
                xpac[chan]['times'].append((timeline[0], timeline[-1]))
                lg.info('Compute PAC ' + chan + ' ' + str((timeline[0], timeline[-1])))
                duration = len(timeline) / sf
                xpac[chan]['duration'].append(duration)
                xpac[chan]['stage'].append(j['stage'])
                xpac[chan]['cycle'].append(j['cycle'])
                xpac[chan]['name'].append(j['name'])

                out = p.filterfit(sf=sf, xpha=dat, xamp=None, axis=1, traxis=0,
                                  nperm=nperm, optimize=optimize,
                                  get_pval=get_pval, get_surro=get_surro,
                                  njobs=njobs)

                if get_pval:

                    if idpac[2] > 0:
                        (xpac[chan]['data'][i, :, :],
                         xpac[chan]['pval'][i, :, :],
                         xpac[chan]['surro'][i, :, :, :]) = (out[0][:, :, 0],
                             out[1], out[2])
                    else:
                        (xpac[chan]['data'][i, :, :],
                         xpac[chan]['pval'][i, :, :]) = (out[0][:, :, 0],
                             out[1])

                elif idpac[2] > 0:
                    (xpac[chan]['data'][i, :, :],
                     xpac[chan]['surro'][i, :, :, :]) = (out[0][:, :, 0],
                         out[1])

                else:
                    xpac[chan]['data'][i, :, :] = out[:, :, 0]

        return xpac, fpha, famp

    def export_freq(self, xfreq):
        """Write frequency analysis data to CSV."""
        filename = splitext(self.filename)[0] + '_freq.csv'

        title_row_1 = ['Segment index',
                       'Start time',
                       'End time',
                       'Duration',
                       'Stitches',
                       'Stage',
                       'Cycle',
                       'Event type',
                       'Channel',
                       ]
        spacer = [''] * (len(title_row_1) - 1)
        freq = list(xfreq[0]['data'].axis['freq'][0])

        xf = asarray([y for x in xfreq for y in x['data']()[0]])
        xf_log = log(xf)
        x_mean = list(mean(xf, axis=0))
        x_sd = list(std(xf, axis=0))
        x_mean_log = list(mean(xf_log, axis=0))
        x_sd_log = list(std(xf_log, axis=0))

        with open(filename, 'w', newline='') as f:
            lg.info('Writing to' + str(filename))
            csv_file = writer(f)
            csv_file.writerow(title_row_1 + freq)
            csv_file.writerow(['Mean'] + spacer + x_mean)
            csv_file.writerow(['SD'] + spacer + x_sd)
            csv_file.writerow(['Mean of log'] + spacer + x_mean_log)
            csv_file.writerow(['SD of log'] + spacer + x_sd_log)
            idx = 0

            for seg in xfreq:

                for chan in seg['data'].axis['chan'][0]:
                    idx += 1
                    data_row = list(seg['data'](chan=chan)[0])
                    csv_file.writerow([idx,
                                       seg['times'][0],
                                       seg['times'][1],
                                       seg['duration'],
                                       seg['n_stitch'],
                                       seg['stage'],
                                       seg['cycle'][2],
                                       seg['name'],
                                       chan,
                                       ] + data_row)

    def export_pac(self, xpac, fpha, famp):
        """Write PAC analysis data to CSV."""
        filename = splitext(self.filename)[0] + '_pac.csv'

        title_row_1 = ['Segment index',
                       'Start time',
                       'End time',
                       'Duration',
                       'Stitch',
                       'Stage',
                       'Cycle',
                       'Event type',
                       'Channel',
                       ]
        spacer = [''] * (len(title_row_1) - 1)
        title_row_2 = []

        for fp in fpha:
            fp_str = str(fp[0]) + '-' + str(fp[1])

            for fa in famp:
                fa_str = str(fa[0]) + '-' + str(fa[1])
                title_row_2.append(fp_str + '_' + fa_str)

        xp = asarray([ravel(chan['data'][x,:,:]) for chan in xpac.values() \
                      for x in range(chan['data'].shape[0])])
        xp_log = log(xp)
        x_mean = list(mean(xp, axis=0))
        x_sd = list(std(xp, axis=0))
        x_mean_log = list(mean(xp_log, axis=0))
        x_sd_log = list(std(xp_log, axis=0))

        with open(filename, 'w', newline='') as f:
            lg.info('Writing to' + str(filename))
            csv_file = writer(f)
            csv_file.writerow(title_row_1 + title_row_2)
            csv_file.writerow(['Mean'] + spacer + x_mean)
            csv_file.writerow(['SD'] + spacer + x_sd)
            csv_file.writerow(['Mean of log'] + spacer + x_mean_log)
            csv_file.writerow(['SD of log'] + spacer + x_sd_log)
            idx = 0

            for chan in xpac.keys():

                for i, j in enumerate(xpac[chan]['times']):
                    idx += 1
                    data_row = list(ravel(xpac[chan]['data'][i,:,:]))
                    csv_file.writerow([idx,
                                       j[0],
                                       j[1],
                                       xpac[chan]['duration'][i],
                                       seg['n_stitch'],
                                       xpac[chan]['stage'][i],
                                       xpac[chan]['cycle'][i][2],
                                       xpac[chan]['name'][i],
                                       chan,
                                       ] + data_row)


def get_times(annot, evt_type=None, stage=None, cycle=None, chan=None,
              exclude=True):
    """Get start and end times for selected segments of data, bundled
    together with info.

    Parameters
    ----------
    annot: instance of Annotations
        The annotation file containing events and epochs
    evt_type: list of str, optional
        Enter a list of event types to get events; otherwise, epochs will
        be returned.
    stage: list of str, optional
        Stage(s) of interest. If None, stage is ignored.
    cycle: list of tuple of two float, optional
        Cycle(s) of interest, as start and end times in seconds from record
        start. If None, cycles are ignored.
    chan: list of str or tuple of None
        Channel(s) of interest, only used for events (epochs have no
        channel). Channel format is 'chan_name (group_name)'.
        If None, channel is ignored.
    exclude: bool
        Exclude epochs by quality. If True, epochs marked as 'Poor' quality
        or staged as 'Artefact' will be rejected (and the signal cisioned
        in consequence). Has no effect on event getting. Defaults to True.

    Returns
    -------
    list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), stage, cycle, chan, name (event type,
        if applicable)

    Notes
    -----
    This function returns epoch or event start and end times, bundled
    together according to the specified parameters.
    Presently, setting exclude to True does not exclude events found in Poor
    signal epochs. The rationale is that events would never be marked in Poor
    signal epochs. If they were automatically detected, these epochs would
    have been left out during detection. If they were manually marked, then
    it must have been Good signal. At the moment, in the GUI, the exclude epoch
    option is disabled when analyzing events, but we could fix the code if we
    find a use case for rejecting events based on the quality of the epoch
    signal.
    """
    getter = annot.get_epochs

    if stage is None:
        stage = (None,)
    if cycle is None:
        cycle = (None,)
    if chan is None:
        chan = (None,)
    if evt_type is None:
        evt_type = (None,)
    elif isinstance(evt_type[0], str):
        getter = annot.get_events
    else:
        lg.error('Event type must be list/tuple of str or None')

    qual = None
    if exclude:
        qual = 'Good'

    bundles = []
    for et in evt_type:

        for ch in chan:

            for cyc in cycle:

                for ss in stage:

                    st_input = ss
                    if ss is not None:
                        st_input = (ss,)

                    evochs = getter(name=et, time=cyc, chan=(ch,),
                                    stage=st_input, qual=qual)
                    if evochs:
                        times = [(e['start'], e['end']) for e in evochs]
                        times = sorted(times, key=lambda x: x[0])
                        one_bundle = {'times': times,
                                      'stage': ss,
                                      'cycle': cyc,
                                      'chan': ch,
                                      'name': et}
                        bundles.append(one_bundle)

    lg.info('bundles: ' + str(bundles))
    return bundles


def concat(bundles, cat=(0, 0, 0, 0)):
    """Prepare events or epochs for concatenation.

    Parameters
    ----------
    bundles : list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), and the stage, cycle, chan and name (event
        type, if applicable) associated with the segment bundle
    cat : tuple of int
        Determines whether and where the signal is concatenated.
        If 1st digit is 1, cycles selected in cycle will be
        concatenated.
        If 2nd digit is 1, different stages selected in stage will be
        concatenated.
        If 3rd digit is 1, discontinuous signal within a same condition
        (stage, cycle, event type) will be concatenated.
        If 4th digit is 1, events of different types will be concatenated.
        0 in any position indicates no concatenation.
        Defaults to (0, 0 , 1, 0), i.e. concatenate signal within stages
        only.

    Returns
    -------
    list of dict
        Each dict has times (the start and end times of each subsegment, as
        list of tuple of float), stage, cycle, as well as chan and event
        type name (empty for epochs). Each bundle comprises a collection of
        subsegments to be concatenated.

    TO-DO
    -----
    Make sure the cat options are orthogonal and make sense
    """
    chan = sorted(set([x['chan'] for x in bundles]))
    cycle = sorted(set([x['cycle'] for x in bundles]))
    stage = sorted(set([x['stage'] for x in bundles]))
    evt_type = sorted(set([x['name'] for x in bundles]))

    all_cycle = None
    all_stage = None
    all_evt_type = None

    if cycle[0] is not None:
        all_cycle = ', '.join([str(c) for c in cycle])
    if stage[0] is not None:
        all_stage = ', '.join(stage)
    if evt_type[0] is not None:
        all_evt_type = ', '.join(evt_type)

    if cat[0]:
        cycle = [all_cycle]

    if cat[1]:
        stage = [all_stage]

    if cat[3]:
        evt_type = [all_evt_type]

    lg.info('Concat ' +  ' ,'.join((str(chan), str(cycle), str(stage), str(evt_type))))

    to_concat = []
    for ch in chan:

        for cyc in cycle:

            for st in stage:

                for et in evt_type:
                    new_times = []

                    for bund in bundles:
                        chan_cond = ch == bund['chan']
                        cyc_cond = cyc in (bund['cycle'], all_cycle)
                        st_cond = st in (bund['stage'], all_stage)
                        et_cond = et in (bund['name'], all_evt_type)

                        if chan_cond and cyc_cond and st_cond and et_cond:
                            new_times.extend(bund['times'])

                    new_times = sorted(new_times, key=lambda x: x[0])
                    new_bund = {'times': new_times,
                              'chan': ch,
                              'cycle': cyc,
                              'stage': st,
                              'name': et
                              }
                    to_concat.append(new_bund)
                    lg.info('new bund ' + str(new_bund))

    if not cat[2]:
        to_concat_new = []

        for bund in to_concat:
            last = None
            bund['times'].append((inf,inf))
            start = 0

            for i, j in enumerate(bund['times']):

                if last is not None:
                    if not isclose(j[0], last, abs_tol=0.1):
                        new_times = bund['times'][start:i]
                        new_bund = bund.copy()
                        new_bund['times'] = new_times
                        to_concat_new.append(new_bund)
                        start = i
                last = j[1]

        to_concat = to_concat_new

    to_concat = [x for x in to_concat if x['times']]

    return to_concat


def divide_bundles(bundles):
    """Take each subsegment inside a bundle and put it in its own bundle,
    copying the bundle metadata.

    Parameters
    ----------
    bundles : list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), and the stage, cycle, (chan and name (event
        type, if applicable) associated with the segment bundle.

    Returns
    -------
    list of one dict
        Dict represents a single segment, and has start and end times (tuple
        of float), stage, cycle, chan and name (event type, if applicable)
    """
    divided = []

    for bund in bundles:
        for t in bund['times']:
            new_bund = bund.copy()
            new_bund['times'] = [t]
            divided.append(new_bund)

    return divided


def find_intervals(bundles, interval):
    """Divide bundles into consecutive segments of a certain duration,
    discarding any remainder.

    Parameters
    ----------
    bundles : list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), and the stage, cycle, (chan and name (event
        type, if applicable) associated with the segment bundle.
        NOTE: Discontinuous segments must already be in separate dicts.
    interval: float
        Duration of consecutive intervals.

    Returns
    -------
    list of dict
        Each dict represents a  segment of duration 'interval', and
        has start and end times (tuple of float), stage, cycle, chan and name
        (event type, if applicable) associated with the single segment.
    """
    segments = []
    for bund in bundles:
        beg, end = bund['times'][0][0], bund['times'][-1][1]

        if end - beg >= interval:
            new_begs = arange(beg, end, interval)[:-1]

            for t in new_begs:
                seg = bund.copy()
                seg['times'] = (t, t + interval)
                segments.append(seg)

    return segments


def longer_than(segments, min_dur):
    """
    Parameters
    ----------
    segments : list of dict
        Each dict has times (the start and end times of each sub-segment, as
        list of tuple of float), and the stage, cycle, chan and name (event
        type, if applicable) associated with the segment
    min_dur: float
        Minimum duration of signal chunks returned.
    """
    if min_dur <= 0.:
        return segments

    long_enough = []
    for seg in segments:

        if sum([t[1] - t[0] for t in seg['times']]) >= min_dur:
            long_enough.append(seg)

    return long_enough


def _create_data_to_analyze(data, analysis_chans, chan_grp, segments,
                            concat_chan=False, evt_chan_only=False):
    """Create data after montage and filtering.

    Parameters
    ----------
    data : instance of ChanTime
        the raw data
    analysis_chans : list of str
        the channel(s) of interest and their reference(s), if any
    chan_grp : dict
        information about channels to plot, to use as reference and about
        filtering etc.
    segments : list of dict
        Each dict has times (the start and end times of each sub-segment, as
        list of tuple of float), stage, cycle, chan, name (event type,
        if applicable). Each dict of subsegments will be concatenated into
        a single segment.
    concat_chan : bool
        If True, signal from different channels will be concatenated into one
        vector. Defaults to False.
    evt_chan_only: bool
        For use with events. If True, only the data on the original channel
        where the event was marked will be returned. If False, data concurrent
        with the event on all channels in analysis_chans will be returned.

    Returns
    -------
    list of dict
        each item is a dict where 'data' is an instance of ChanTime for a
        single segment of signal, 'name' is the event type, if applicable, and
        with 'chan' (str), 'stage' (str) and 'cycle' (int)
    """
    s_freq = data.s_freq
    output = []

    for seg in segments:
        lg.info('_create: Looping over one segment')
        times = [(int(t0 * s_freq),
                  int(t1 * s_freq)) for (t0, t1) in seg['times']]
        n_stitch = len(times) - 1

        one_segment = ChanTime()
        one_segment.s_freq = s_freq
        one_segment.axis['chan'] = empty(1, dtype='O')
        one_segment.axis['time'] = empty(1, dtype='O')
        one_segment.data = empty(1, dtype='O')

        all_epoch_data = []
        timeline = []
        all_chan_grp_name = []

        if evt_chan_only and seg['chan'] is not '':
            these_chans = [seg['chan'].split(' (')[0]]
        else:
            these_chans = analysis_chans

        for chan in these_chans:
            chan_grp_name = chan + ' (' + chan_grp['name'] + ')'
            all_chan_grp_name.append(chan_grp_name)

        sel_data = _select_channels(data,
                                    these_chans +
                                    chan_grp['ref_chan'])
        data1 = montage(sel_data, ref_chan=chan_grp['ref_chan'])

        data1.data[0] = nan_to_num(data1.data[0])

        for (t0, t1) in times:
            one_interval = data.axis['time'][0][t0: t1]
            lg.info('_create: ' + str((t0, t1)))
            timeline.append(one_interval)
            epoch_dat = empty((len(these_chans), len(one_interval)))
            i_ch = 0

            for chan in these_chans:
                dat = data1(chan=chan, trial=0)
                #dat = dat - nanmean(dat)
                epoch_dat[i_ch, :] = dat[t0: t1]
                i_ch += 1

            all_epoch_data.append(epoch_dat)

        one_segment.axis['chan'][0] = asarray(all_chan_grp_name, dtype='U')
        one_segment.axis['time'][0] = concatenate(timeline)
        lg.info('_create, concatenated: ' + str((one_segment.axis['time'][0][0], one_segment.axis['time'][0][-1])))
        one_segment.data[0] = concatenate(all_epoch_data, axis=1)

        if concat_chan and len(one_segment.axis['chan'][0]) > 1:
            one_segment.data[0] = ravel(one_segment.data[0])
            one_segment.axis['chan'][0] = asarray([(', ').join(
                    all_chan_grp_name)], dtype='U')
            # axis['time'] should not be used in this case

        lg.info('_created seg with chan ' + str(one_segment.axis['chan'][0]))

        output.append({'data': one_segment,
                       'chan': these_chans,
                       'stage': seg['stage'],
                       'cycle': seg['cycle'],
                       'name': seg['name'],
                       'n_stitch': n_stitch})

    return output

def _select_channels(data, channels):
    """Select channels.

    Parameters
    ----------
    data : instance of ChanTime
        data with all the channels
    channels : list
        channels of interest

    Returns
    -------
    instance of ChanTime
        data with only channels of interest

    Notes
    -----
    This function does the same as sleepytimes.trans.select, but it's much faster.
    sleepytimes.trans.Select needs to flexible for any data type, here we assume
    that we have one trial, and that channel is the first dimension.

    """
    output = data._copy()
    chan_list = list(data.axis['chan'][0])
    idx_chan = [chan_list.index(i_chan) for i_chan in channels]
    output.data[0] = data.data[0][idx_chan, :]
    output.axis['chan'][0] = asarray(channels)

    return output
