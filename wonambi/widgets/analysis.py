# -*- coding: utf-8 -*-

"""Dialogs for analyses, such as power spectra, PAC, event parameters
"""
from datetime import timedelta
from functools import partial
from itertools import compress
from logging import getLogger
from numpy import (asarray, concatenate, diff, empty, floor, in1d, inf, log,
                   logical_and, mean, ptp, sqrt, square, std)
from scipy.signal import periodogram
from math import isclose
from os.path import basename, splitext
from pickle import dump, load
#from tensorpac.pacstr import pacstr

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (QAbstractItemView,
                             QAction,
                             QCheckBox,
                             QComboBox,
                             QDialog,
                             QDialogButtonBox,
                             QFileDialog,
                             QFormLayout,
                             QGridLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QInputDialog,
                             QLabel,
                             QLineEdit,
                             QListWidget,
                             QListWidgetItem,
                             QMessageBox,
                             QPushButton,
                             QTableWidget,
                             QTableWidgetItem,
                             QTabWidget,
                             QVBoxLayout,
                             QWidget,
                             QScrollArea,
                             )

from .. import ChanTime
from ..trans import montage, filter_
from ..detect import DetectSpindle, DetectSlowWave, merge_close
from .settings import (Config, FormStr, FormInt, FormFloat, FormBool, FormMenu,
                       FormRadio)

lg = getLogger(__name__)

STAGE_NAME = ['NREM1', 'NREM2', 'NREM3', 'REM', 'Wake', 'Movement',
              'Undefined', 'Unknown', 'Artefact', 'Unrecognized']
POWER_METHODS = ['Welch', 'Multitaper']

class AnalysisDialog(QDialog):
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
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent

        self.setWindowTitle('Analysis')
        self.setWindowModality(Qt.ApplicationModal)
        self.groups = self.parent.channels.groups
        self.chunk = {}
        self.label = {}
        self.cat = {}
        self.trans = {}
        self.event_types = None
        self.cycles = None
        self.event = {}
        self.psd = {}
        self.psd['welch'] = {}
        self.psd['mtap'] = {}
        self.pac = {}

        self.create_dialog()

    def create_dialog(self):
        """Create the dialog."""
        bbox = QDialogButtonBox(QDialogButtonBox.Help | QDialogButtonBox.Ok |
                QDialogButtonBox.Cancel)
        self.idx_help = bbox.button(QDialogButtonBox.Help)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)

        """ ------ CHUNKING ------ """

        box0 = QGroupBox('Chunking')

        self.chunk['event'] = FormRadio('by e&vent')
        self.chunk['epoch'] = FormRadio('by e&poch')
        self.chunk['segment'] = FormRadio('by &segment')
        self.label['evt_type'] = QLabel('Event type')
        self.label['epoch_dur'] = QLabel('Duration (s)')
        self.label['min_dur'] = QLabel('Minimum duration (s)')
        self.epoch_dur = FormFloat(30.0)
        self.lock_to_staging = FormBool('Lock to staging epochs')
        self.min_dur = FormFloat(0.0)

        evt_box = QListWidget()
        evt_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_evt_type = evt_box

        grid = QGridLayout(box0)
        box0.setLayout(grid)
        grid.addWidget(self.chunk['event'], 0, 0)
        grid.addWidget(self.label['evt_type'], 1, 0)
        grid.addWidget(self.idx_evt_type, 1, 1, 1, 2)
        grid.addWidget(self.chunk['epoch'], 2, 0)
        grid.addWidget(self.label['epoch_dur'], 2, 1)
        grid.addWidget(self.epoch_dur, 2, 2)
        grid.addWidget(self.lock_to_staging, 3, 0, 1, 3)
        grid.addWidget(self.chunk['segment'], 4, 0)
        grid.addWidget(self.label['min_dur'], 5, 0)
        grid.addWidget(self.min_dur, 5, 2)

        """ ------ LOCATION ------ """

        box1 = QGroupBox('Location')

        self.idx_group = FormMenu([gr['name'] for gr in self.groups])

        chan_box = QListWidget()
        chan_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_chan = chan_box

        cycle_box = QListWidget()
        cycle_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_cycle = cycle_box

        stage_box = QListWidget()
        stage_box.addItems(STAGE_NAME) # TODO: make it find what stages were scored
        stage_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_stage = stage_box

        self.reject_bad = FormBool('Exclude Artefact/Poor signal epochs')

        form_layout = QFormLayout()
        box1.setLayout(form_layout)
        form_layout.addRow('Channel group',
                            self.idx_group)
        form_layout.addRow('Channel(s)',
                            self.idx_chan)
        form_layout.addRow('Cycle(s)',
                            self.idx_cycle)
        form_layout.addRow('Stage(s)',
                            self.idx_stage)
        form_layout.addRow(self.reject_bad)

        """ ------ CONCATENATION ------ """

        box_c = QGroupBox('Concatenation')

        self.cat['chan'] = FormBool('Concatenate channels')
        self.cat['cycle'] = FormBool('Concatenate cycles')
        self.cat['within_stage'] = FormBool('Concatenate within stage')
        self.cat['between_stages'] = FormBool(''
                        'Concatenate between stages')

        for box in self.cat.values():
            box.setEnabled(False)

        form_layout = QFormLayout()
        box_c.setLayout(form_layout)
        form_layout.addRow(self.cat['chan'])
        form_layout.addRow(self.cat['cycle'])
        form_layout.addRow(self.cat['between_stages'])
        form_layout.addRow(self.cat['within_stage'])

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

        form_layout = QFormLayout()
        box2.setLayout(form_layout)
        form_layout.addRow(tb['none'])
        form_layout.addRow(tb['butter'])
        form_layout.addRow(tb['cheby'])
        form_layout.addRow(tb['bessel'])
        form_layout.addRow(*filt['order'])
        form_layout.addRow(filt['bandpass_l'][0])
        form_layout.addRow(*filt['f1'])
        form_layout.addRow(*filt['f2'])
        form_layout.addRow(filt['notch_l'][0])
        form_layout.addRow(*filt['notch_centre'])
        form_layout.addRow(*filt['notch_bandw'])

        """ ------ EVENTS ------ """

        tab1 = QWidget()

        ev = self.event
        ev['count'] = FormBool('Count')
        ev['density'] = FormBool('Density, per (s)')
        ev['density_per'] = FormFloat(default=30.0)
        ev['all_local'] = FormBool('All'), FormBool('')

        ev['local'] = {}
        el = ev['local']
        el['dur'] = FormBool('Duration (s)'), FormBool('')
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
        ev['sw']['slope'] = []
        for i in range(10):
            ev['sw']['slope'].append(FormBool(''))

        box_global = QGroupBox('Global')

        grid1 = QGridLayout(box_global)
        grid1.addWidget(ev['count'], 0, 0)
        grid1.addWidget(ev['density'], 1, 0)
        grid1.addWidget(ev['density_per'], 1, 1)

        box_local = QGroupBox('Local')

        grid2 = QGridLayout(box_local)
        grid2.addWidget(QLabel('Parameter'), 0, 0)
        grid2.addWidget(QLabel('  '), 0, 1)
        grid2.addWidget(QLabel('Pre-process'), 0, 2)
        grid2.addWidget(ev['all_local'][0], 1, 0)
        grid2.addWidget(ev['all_local'][1], 1, 2)
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
        for i,w in enumerate(ev['sw']['slope']):
            x = floor(i/5)
            grid3.addWidget(w, i - 5 * x + 3, x + 1)

        vlayout = QVBoxLayout(tab1)
        vlayout.addWidget(box_global)
        vlayout.addWidget(box_local)
        vlayout.addWidget(box_sw)
        vlayout.addStretch(1)

        """ ------ PSD ------ """

        tab2 = QWidget()

        box_welch = QGroupBox('Welch')

        self.psd['welch_on'] = FormBool("Welch's method")
        welch = self.psd['welch']
        welch['win_dur'] = FormFloat(default=1.)
        welch['overlap'] = FormFloat(default=0.5)
        welch['fft_dur'] = FormFloat()
        welch['window'] = FormMenu(['boxcar', 'triang', 'blackman',
                'hamming', 'hann', 'bartlett', 'flattop', 'parzen', 'bohman',
                'blackmanharris', 'nuttall', 'barthann'])
        welch['detrend'] = FormMenu(['constant', 'linear'])
        welch['scaling'] = FormMenu(['density', 'spectrum'])
        welch['trans'] = FormBool('Pre-process')

        welch['win_dur_l'] = QLabel('Window length (s)')
        welch['overlap_l'] = QLabel('Overlap ratio')
        welch['fft_dur_l'] = QLabel('FFT length (s)')
        welch['window_l'] = QLabel('Window type')
        welch['detrend_l'] = QLabel('Detrend')
        welch['scaling_l'] = QLabel('Scaling')

        form_layout = QFormLayout()
        box_welch.setLayout(form_layout)
        form_layout.addRow(self.psd['welch_on'])
        form_layout.addRow(welch['win_dur_l'],
                           welch['win_dur'])
        form_layout.addRow(welch['overlap_l'],
                           welch['overlap'])
        form_layout.addRow(welch['fft_dur_l'],
                           welch['fft_dur'])
        form_layout.addRow(welch['window_l'],
                           welch['window'])
        form_layout.addRow(welch['detrend_l'],
                           welch['detrend'])
        form_layout.addRow(welch['scaling_l'],
                           welch['scaling'])
        form_layout.addRow(welch['trans'])

        box_mtap = QGroupBox('Multitaper')

        self.psd['mtap_on'] = FormBool("Multitaper method")
        mtap = self.psd['mtap']
        mtap['fmin'] = FormFloat(default=0.)
        mtap['fmax'] = FormFloat(default=inf)
        mtap['bandwidth'] = FormFloat()
        mtap['adaptive'] = FormBool('Adaptive weights')
        mtap['low_bias'] = FormBool('Low bias')
        mtap['normalization'] = FormMenu(['full', 'length'])
        mtap['trans'] = FormBool('Pre-process')

        mtap['fmin_l'] = QLabel('Minimum frequency (Hz)')
        mtap['fmax_l'] = QLabel('Maximum frequency (Hz)')
        mtap['bandwidth_l'] = QLabel('Bandwidth (Hz)')
        mtap['normalization_l'] = QLabel('Normalization (Hz)')

        form_layout = QFormLayout()
        box_mtap.setLayout(form_layout)
        form_layout.addRow(self.psd['mtap_on'])
        form_layout.addRow(mtap['fmin_l'],
                           mtap['fmin'])
        form_layout.addRow(mtap['fmax_l'],
                           mtap['fmax'])
        form_layout.addRow(mtap['bandwidth_l'],
                           mtap['bandwidth'])
        form_layout.addRow(mtap['normalization_l'],
                           mtap['normalization'])
        form_layout.addRow(mtap['adaptive'])
        form_layout.addRow(mtap['low_bias'])
        form_layout.addRow(mtap['trans'])

        for button in welch.values():
            button.setEnabled(False)
        for button in mtap.values():
            button.setEnabled(False)

        vlayout = QVBoxLayout(tab2)
        vlayout.addWidget(box_welch)
        vlayout.addWidget(box_mtap)
        vlayout.addStretch(1)

        """ ------ PAC ------ """

        tab3 = QWidget()

        # placeholders for now
        pac_metrics = ['Mean Vector Length',
                       'Kullback-Leiber Distance',
                       'Heights ratio',
                       'ndPac',
                       'Phase-Synchrony']
        pac_surro = ['No surrogates',
                     'Swap phase/amplitude across trials',
                     'Swap amplitude blocks across time',
                     'Shuffle amplitude time-series',
                     'Time lag']
        pac_norm = ['No normalization',
                    'Substract the mean of surrogates',
                    'Divide by the mean of surrogates',
                    'Substract then divide by the mean of surrogates',
                    "Substract the mean and divide by the deviation of " + \
                    "the surrogates"]
        """
        pac_metrics = [pacstr((x, 0, 0))[0] for x in range(1,6)]
        pac_metrics = [x[:x.index('(') - 1] for x in pac_metrics]
        pac_metrics[1] = 'Kullback-Leibler Distance' # corrected typo
        pac_surro = [pacstr((1, x, 0))[1] for x in range(5)]
        pac_norm = [pacstr((1, 0, x))[2] for x in range(5)]
        """
        pac = self.pac

        box_complex = QGroupBox('Complex definition')

        pac['hilbert_on'] = FormRadio('Hilbert transform')
        pac['hilbert'] = {}
        hilb = pac['hilbert']
        hilb['filt'] = QLabel('Filter'), FormMenu(['fir1', 'butter', 'bessel'])
        hilb['cycle_pha'] = QLabel('Cycles, phase'), FormInt(default=3)
        hilb['cycle_amp'] = QLabel('Cycles, amp'), FormInt(default=6)
        hilb['order'] = QLabel('Order'), FormInt(default=3)
        pac['wavelet_on'] = FormRadio('Wavelet convolution')
        pac['wav_width'] = QLabel('Width'), FormInt(default=7)

        grid = QGridLayout(box_complex)
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

        box_metric = QGroupBox('PAC metric')

        pac['metric'] = FormMenu(pac_metrics)
        pac['fpha'] = FormStr()
        pac['famp'] = FormStr()
        pac['nbin'] = QLabel('Number of bins'), FormInt(default=18)

        form_layout = QFormLayout(box_metric)
        form_layout.addRow('PAC metric',
                           pac['metric'])
        form_layout.addRow('Phase frequencies (Hz)',
                           pac['fpha'])
        form_layout.addRow('Amplitude frequencies (Hz)',
                           pac['famp'])
        form_layout.addRow(*pac['nbin'])

        box_surro = QGroupBox('Surrogate data')

        pac['surro_method'] = FormMenu(pac_surro)
        pac['surro'] = {}
        sur = pac['surro']
        sur['nperm'] = QLabel('Number of surrogates'), FormInt(default=200)
        sur['nblocks'] = (QLabel('Number of amplitude blocks'),
                          FormInt(default=2))
        sur['pval'] = FormBool('Get p-values'), None
        sur['save_surro'] = FormBool('Save surrogate data'), None
        sur['norm'] = FormMenu(pac_norm), None

        form_layout = QFormLayout(box_surro)
        form_layout.addRow(pac['surro_method'])
        form_layout.addRow(*sur['nperm'])
        form_layout.addRow(*sur['nblocks'])
        form_layout.addRow(sur['pval'][0])
        form_layout.addRow(sur['save_surro'][0])
        form_layout.addRow(sur['norm'][0])

        box_opts = QGroupBox('Options')

        pac['optimize'] = FormMenu(['True', 'False', 'greedy', 'optimal'])
        pac['njobs'] = FormInt(default=-1)

        form_layout = QFormLayout(box_opts)
        form_layout.addRow('Optimize einsum',
                           pac['optimize'])
        form_layout.addRow('Number of jobs',
                           pac['njobs'])

        vlayout = QVBoxLayout(tab3)
        vlayout.addWidget(box_complex)
        vlayout.addWidget(box_metric)
        vlayout.addWidget(box_surro)
        vlayout.addWidget(box_opts)

        """ ------ TRIGGERS ------ """

        for button in self.chunk.values():
            button.toggled.connect(self.toggle_buttons)

        for lw in [self.idx_chan, self.idx_cycle, self.idx_stage]:
            lw.itemSelectionChanged.connect(self.toggle_concatenate)

        for button in self.trans['button'].values():
            button.toggled.connect(self.toggle_buttons)

        for button in [x[0] for x in self.event['local'].values()]:
            button.connect(self.toggle_buttons)

        self.idx_group.connect(self.update_channels)
        ev['density'].connect(self.toggle_buttons)
        ev['all_local'][0].connect(self.check_all_local)
        ev['all_local'][1].connect(self.check_all_local)
        ev['sw']['all_slope'].connect(self.check_all_slopes)
        self.psd['welch_on'].connect(self.toggle_buttons)
        self.psd['mtap_on'].connect(self.toggle_buttons)
        pac['hilbert_on'].toggled.connect(self.toggle_buttons)
        pac['wavelet_on'].toggled.connect(self.toggle_buttons)
        pac['metric'].connect(self.toggle_buttons)
        pac['surro_method'].connect(self.toggle_buttons)
        bbox.clicked.connect(self.button_clicked)

        """ ------ SET DEFAULTS ------ """

        self.chunk['segment'].setChecked(True)
        self.reject_bad.setChecked(True)
        self.trans['button']['none'].setChecked(True)
        el['dur'][1].set_value(False)
        mtap['low_bias'].setChecked(True)
        pac['hilbert_on'].setChecked(True)
        pac['metric'].set_value('Kullback-Leibler Distance')
        pac['optimize'].set_value('False')

        """ ------ LAYOUT MASTER ------ """

        box3 = QTabWidget()

        box3.addTab(tab1, 'Events')
        box3.addTab(tab2, 'PSD')
        box3.addTab(tab3, 'PAC')

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout1 = QVBoxLayout()
        vlayout1.addWidget(box0)
        vlayout1.addWidget(box1)
        vlayout1.addWidget(box_c)
        vlayout1.addStretch(1)

        vlayout2 = QVBoxLayout()
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

    def update_types(self):
        """Update the event types list when dialog is opened."""
        self.event_types = self.parent.notes.annot.event_types
        self.idx_evt_type.clear()
        for ev in self.event_types:
            self.idx_evt_type.addItem(ev)

    def update_groups(self):
        """Update the channel groups list when dialog is opened."""
        self.groups = self.parent.channels.groups
        self.idx_group.clear()
        for gr in self.groups:
            self.idx_group.addItem(gr['name'])

        self.update_channels()

    def update_channels(self):
        """Update the channels list when a new group is selected."""
        group_dict = {k['name']: i for i, k in enumerate(self.groups)}
        group_index = group_dict[self.idx_group.currentText()]
        self.one_grp = self.groups[group_index]

        self.idx_chan.clear()

        for chan in self.one_grp['chan_to_plot']:
            self.idx_chan.addItem(chan)

    def update_cycles(self):
        """Enable cycles checkbox only if there are cycles marked, with no
        errors."""
        try:
            self.cycles = self.parent.notes.annot.get_cycles()

        except ValueError as err:
            self.idx_cycle.setEnabled(False)
            msg = 'There is a problem with the cycle markers: ' + str(err)
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)

        else:
            if self.cycles is None:
                self.idx_cycle.setEnabled(False)
            else:
                self.idx_cycle.setEnabled(True)

    def toggle_buttons(self):
        """Enable and disable buttons, according to options selected."""
        event_on = self.chunk['event'].isChecked()
        epoch_on = self.chunk['epoch'].isChecked()
        segment_on = self.chunk['segment'].isChecked()

        self.label['evt_type'].setEnabled(event_on)
        self.idx_evt_type.setEnabled(event_on)
        self.label['epoch_dur'].setEnabled(epoch_on)
        self.epoch_dur.setEnabled(epoch_on)
        self.cat['within_stage'].setChecked(segment_on)
        self.cat['within_stage'].setEnabled(not segment_on)

        filter_on = not self.trans['button']['none'].isChecked()
        for button in self.trans['filt'].values():
            button[0].setEnabled(filter_on)
            if button[1] is not None:
                button[1].setEnabled(filter_on)

        density_on = self.event['density'].isChecked()
        self.event['density_per'].setEnabled(density_on)

        for buttons in self.event['local'].values():
            checked = buttons[0].isChecked()
            buttons[1].setEnabled(checked)
            if not checked:
                buttons[1].setChecked(False)

        welch_on =  self.psd['welch_on'].get_value()
        mtap_on = self.psd['mtap_on'].get_value()
        for button in self.psd['welch'].values():
            button.setEnabled(welch_on)
        for button in self.psd['mtap'].values():
            button.setEnabled(mtap_on)

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

    def toggle_concatenate(self):
        """Enable and disable concatenation options."""
        for i,j in zip([self.idx_chan, self.idx_cycle, self.idx_stage],
               [self.cat['chan'], self.cat['cycle'],
                self.cat['between_stages']]):
            if len(i.selectedItems()) > 1:
                j.setEnabled(True)
            else:
                j.setEnabled(False)
                j.setChecked(False)

    def check_all_local(self):
        """Check or uncheck all local event parameters."""
        all_local_checked = self.event['all_local'][0].isChecked()
        if not all_local_checked:
            self.event['all_local'][1].setChecked(False)
        all_local_pp_checked = self.event['all_local'][1].isChecked()
        self.event['all_local'][1].setEnabled(all_local_checked)
        for buttons in self.event['local'].values():
            buttons[0].setChecked(all_local_checked)
            buttons[1].setEnabled(buttons[0].isChecked())
            buttons[1].setChecked(all_local_pp_checked)

    def check_all_slopes(self):
        """Check and uncheck slope options"""
        slopes_checked = self.event['sw']['all_slope'].get_value()
        for button in self.event['sw']['slope']:
            button.setChecked(slopes_checked)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:
            """
            evt_type = self.idx_evt_type.currentText()
            stage = self.idx_stage.selectedItems()
            cycle = self.parent.annot.get_cycles() # TO-DO: get cycles
            exclude = 
            group = self.one_grp
            chan = self.get_channels()
            evt_chan_only = 
            params = {k: v.get_value() for k, v in self.chunk.items()}
            
            
            bundles = self.get_times(evt_type=evt_type, stage=self.stage, 
                                   cycle=cycle, chan=chan, exclude=exclude)
            bundles = self.remove_artf_evts(bundles)
            self.read_data(chan, group, bundles, evt_chan_only)
            
            
            
            
            if self.filename is None:
                return

            freqs = (self.frequency['locut'].get_value(),
                     self.frequency['hicut'].get_value())

            if None in freqs:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            filename = self.filename
            
            chan_name = chan + ' (' + self.idx_group.currentText() + ')'
            params = [k for k, v in self.index.items() if v.get_value()]
            cycles = None
            fsplit = None

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]

            if self.cyc_split.get_value():
                cycles = self.cycles

            if self.freq_split.get_value():
                fsplit = float(self.freq_cutoff.text())

            self.parent.notes.read_data(chan, self.one_grp)

            summary, events = self.parent.notes.analyze_events(evt_type,
                                                             chan_name,
                                                             stage,
                                                             params,
                                                             frequency=freqs,
                                                             cycles=cycles,
                                                             fsplit=fsplit)

            self.parent.notes.annot.export_event_data(filename, summary,
                                                      events, cycles=cycles,
                                                      fsplit=fsplit)
            """
            self.accept()

        if button is self.idx_cancel:
            self.reject()

    def read_data(self, chan, group, bundles, evt_chan_only):
        """Read data for analysis."""
        dataset = self.parent.info.dataset
        chan = self.get_channels()
        chan_to_read = chan + self.one_grp['ref_chan']

        data = dataset.read_data(chan=chan_to_read)

        max_s_freq = self.parent.value('max_s_freq')
        if data.s_freq > max_s_freq:
            q = int(data.s_freq / max_s_freq)
            lg.debug('Decimate (no low-pass filter) at ' + str(q))

            data.data[0] = data.data[0][:, slice(None, None, q)]
            data.axis['time'][0] = data.axis['time'][0][slice(None, None, q)]
            data.s_freq = int(data.s_freq / q)
        
        self.data = _create_data_to_analyze(data, chan, self.one_grp, 
                                            bundles=bundles, 
                                            evt_chan_only=evt_chan_only)

    def get_times(self, evt_type=None, stage=None, cycle=None, chan=None,
                  exclude=True):
        """Get start and end times for selected segments of data, bundled
        together with info.

        Parameters
        ----------
        evt_type: list of str, optional
            Enter a list of event types to get events; otherwise, epochs will
            be returned.
        stage: list of str, optional
            Stage(s) of interest. If None, all stages are used.
        cycle: list of tuple of two float, optional
            Cycle(s) of interest, as start and end times in seconds from record
            start. If None, cycles are disregarded.
        chan: list of str or tuple of None
            Channel(s) of interest, only used for events (epochs have no 
            channel). If None, channels are disregarded.
        exclude: bool
            Exclude epochs by quality. If True, epochs marked as 'Poor' quality
            or staged as 'Artefact' will be rejected (and the signal cisioned 
            in consequence). Defaults to True.
            
        Returns
        -------
        list of dict
            Each dict has times (the start and end times of each segment, as
            list of tuple of float), stage, cycle, chan, name (event type,
            if applicable)
            
        Notes
        -----
        This function returns epoch or event start and end times, bundled 
        together according to the specified parameters. The times list will not
        necessarily be chronological.
        """      
        getter = self.annot.get_epochs

        if stage is None:
            stage = (None,)
        if cycle is None:
            cycle = (None,)
        if chan is None:
            chan = (None,)  
        if evt_type is None:
            evt_type = (None,)
        elif isinstance(evt_type[0], str):
            getter = self.annot.get_events
        else:
            lg.error('Event type must be list/tuple of str or None')
            
        qual = None
        if exclude:
            qual = 'Poor'
        
        bundles = []
        for et in evt_type:
            
            for ch in chan:

                for cyc in cycle:

                    for ss in stage:

                        evochs = getter(name=et, time=cyc, chan=ch,
                                        stage=ss, qual=qual)
                        times = [(e['start'], e['end']) for e in evochs]
                        times = sorted(times, key=lambda x: x['start'])
                        one_bundle = {'times': times,
                                      'stage': ss,
                                      'cycle': cyc,
                                      'chan': ch,
                                      'name': et}
                        bundles.append(one_bundle)

        return bundles

    def remove_artf_evts(self, bundles):
        """Correct times to remove events marked 'Artefact'.
        
        Parameters
        ----------
        bundles : list of dict
            Each dict has times (the start and end times of each segment, as
            list of tuple of float), and the stage, cycle, chan and name (event
            type, if applicable) associated with the segment bundle

        Returns
        -------
        list of dict
            Each dict has times (the start and end times of each segment, as 
            list of tuple of float), stage, cycle, as well as chan and event
            type name (empty for epochs)            
        """
        for bund in bundles:
            times = bund['times']
            beg = times[0][0]
            end = times[-1][-1]
            stage = bund['stage']
        
            artefact = self.annot.get_events(name='Artefact', time=(beg, end), 
                                             stage=stage, qual='Good')
            
            if artefact is not None:
                new_times = []
                
                for artf in artefact:
                    
                    for seg in times:
                        a_starts_in_s = seg[0] <= artf[0] <= seg[1]
                        a_ends_in_s = seg[0] <= artf[1] <= seg[1]
                        
                        if a_ends_in_s and not a_starts_in_s:
                            seg[0] = artf[1]                 
                            
                        elif a_starts_in_s:
                            seg[1] = artf[0]

                            if a_ends_in_s:
                                new_times.append((artf[1], seg[1]))
                            
                        new_times.append(seg)
                        
                bund['times'] = new_times                
            
        return bundles                

    def concat(self, bundles, cat=(0, 0, 1, 0)):
        """Concatenate events or epochs.

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
            Each dict has times (the start and end times of each segment, as 
            list of tuple of float), stage, cycle, as well as chan and event
            type name (empty for epochs)
            
        TO-DO
        -----
        Make sure the cat options are orthogonal and make sense
        """   
        chan = list(set([x['chan'] for x in bundles]))
        cycle = sorted(set([x['cycle'] for x in bundles]))
        stage = set([x['stage'] for x in bundles])
        evt_type = set([x['name'] for x in bundles])        
        
        # since events are channel-specific, they must be sorted by channel
        if chan == ['']:
            all_chan = ', '.join(chan)
            chan = [all_chan]
        
        if cat[0]:
            all_cycle = ', '.join([str(c) for c in cycle])
            cycle = [all_cycle]
            
        if cat[1]:
            all_stage = ', '.join(stage)
            stage = [all_stage]
            
        if cat[3]:
            all_evt_type = ', '.join(evt_type)
            evt_type = [all_evt_type]
            
        to_concat = []
        for ch in chan:

            for cyc in cycle:

                for st in stage:

                    for et in evt_type:
                        new_times = []
                        
                        for bund in bundles:
                            chan_cond = ch in (bund['chan'], all_chan)
                            cyc_cond = cyc in (bund['cycle'], all_cycle)
                            st_cond = st in (bund['stage'], all_stage)
                            et_cond = et in (bund['name'], all_evt_type)
                            
                            if logical_and(chan_cond, cyc_cond, st_cond, 
                                           et_cond):
                                new_times.extend(bund['times'])
                                
                        new_bund = {'times': new_times,
                                  'chan': ch,
                                  'cycle': cyc,
                                  'stage': st,
                                  'name': et
                                  }
                        to_concat.append(new_bund)

        if not cat[2]:            
            to_concat_new = []
            
            for bund in to_concat:                
                last = None
                
                for i, j in enumerate(bund['times'].append((inf,inf))):
                    
                    if last is not None:                       
                        if not isclose(j[0], last, abs_tol=0.1):
                            new_times = bund['times'][:i]
                            new_bund = bund.copy()
                            new_bund['times'] = new_times
                            to_concat_new.append(bund['times'][:i])
                    last = j[1]
            
            to_concat = to_concat_new
                    
        return to_concat


    def longer_than(self, bundles, min_dur):
        """
        Parameters
        ----------
        bundles : list of dict
            Each dict has times (the start and end times of each segment, as 
            list of tuple of float), and the stage, cycle, chan and name (event 
            type, if applicable) associated with the segment bundle
        min_dur: float
            Minimum duration of signal chunks returned.
        """
        if min_dur <= 0:
            return bundles
        
        long_enough = []
        for bund in bundles:
        
            if sum([t[1] - t[0] for t in bund['times']]) >= min_dur:
                long_enough.append(bund)
        
        return long_enough


def _create_data_to_analyze(data, analysis_chans, chan_grp, bundles, 
                            evt_chan_only=True):
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
    times : list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), stage, cycle, chan, name (event type,
        if applicable)
    evt_chan_only: bool
        For use with events. If True, data concurrent with the event on all
        channels in analysis_chans will be returned. If False, only the data
        on the original channel where the event was marked will be returned.

    Returns
    -------
    instance of ChanTime
        data ready to be analyzed. one trial only.
    """
    s_freq = data.s_freq
    output = {}

    for bund in bundles:
        times = [(int(t0 * s_freq),
                  int(t1 * s_freq)) for (t0, t1) in bundles['times']]        

        one_segment = ChanTime()
        one_segment.s_freq = s_freq
        one_segment.axis['chan'] = empty(1, dtype='O')
        one_segment.axis['time'] = empty(1, dtype='O')
        one_segment.data = empty(1, dtype='O')
    
        all_epoch_data = []
        clock_time = []
        all_chan_grp_name = []
        
        if evt_chan_only and bund['chan'] is not None:
            these_chans = bund['chan']
        else:
            these_chans = analysis_chans
    
        for chan in these_chans:
            chan_grp_name = chan + ' (' + chan_grp['name'] + ')'
            all_chan_grp_name.append(chan_grp_name)
    
        sel_data = _select_channels(data,
                                    these_chans +
                                    chan_grp['ref_chan'])
        data1 = montage(sel_data, ref_chan=chan_grp['ref_chan'])
    
        for (t0, t1) in times:
            one_interval = data.axis['time'][0][t0: t1]
            clock_time.append(one_interval)
            epoch_dat = empty((len(these_chans), len(one_interval)))
            i_ch = 0
    
            for chan in these_chans:
                dat = data1(chan=chan, trial=0)
                #dat = dat - nanmean(dat)
                epoch_dat[i_ch, :] = dat[t0: t1]
                i_ch += 1
    
            all_epoch_data.append(epoch_dat)
    
        one_segment.axis['chan'][0] = asarray(all_chan_grp_name, dtype='U')
        one_segment.axis['time'][0] = concatenate(clock_time)
        one_segment.data[0] = concatenate(all_epoch_data, axis=1)
        output.update({'data': one_segment,
                       'chan': bund['chan'],
                       'stage': bund['stage'],
                       'cycle': bund['cycle'],
                       'name': bund['name']})

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