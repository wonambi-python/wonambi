# -*- coding: utf-8 -*-

"""Dialogs for analyses, such as power spectra, PAC, event parameters
"""
from logging import getLogger

from numpy import (amax, amin, asarray, concatenate, diff, empty, 
                   floor, gradient, hstack, in1d, log, logical_and, logical_or, 
                   mean, nan, nan_to_num, negative, ones, ptp, ravel, reshape, 
                   sign, sqrt, square, std, where, zeros)
from scipy.signal import fftconvolve
from itertools import compress
from csv import writer
from os.path import basename, splitext
from pickle import dump

try:
    from matplotlib.backends.backend_qt5agg \
        import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg \
        import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
except ImportError:
    FigureCanvas = object
    Figure = None

try:
    from tensorpac import Pac
    from tensorpac.pacstr import pacstr
except ImportError:
    Pac = pacstr = None

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView,
                             QDialog,
                             QDialogButtonBox,
                             QDoubleSpinBox,
                             QFileDialog,
                             QFormLayout,
                             QGridLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QListWidget,
                             QProgressDialog,
                             QPushButton,
                             QSizePolicy,
                             QTabWidget,
                             QVBoxLayout,
                             QWidget,
                             )

from .. import ChanTime
from ..trans import (math, montage, filter_, frequency, remove_artf_evts, 
                     _select_channels, get_times, longer_than, _concat, 
                     divide_bundles, find_intervals)
from .modal_widgets import ChannelDialog
from .utils import (FormStr, FormInt, FormFloat, FormBool, FormMenu, FormRadio,
                    FormSpin, freq_from_str, short_strings, STAGE_NAME)

lg = getLogger(__name__)


class AnalysisDialog(ChannelDialog):
    """Dialog for specifying various types of analyses: per event, per epoch or
    per entire segments of signal. PSD, PAC, event metrics. Option to transform
    signal before analysis. Creates a pickle object.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window
    nseg : int
        number of segments in current selection        
    idx_evt_type : QListWidget
        List of all event types from Annotations
    """
    def __init__(self, parent):
        ChannelDialog.__init__(self, parent)

        self.setWindowTitle('Analysis console')
        self.chunk = {}
        self.label = {}
        self.cat = {}
        self.trans = {}
        self.event_types = None
        self.event = {}
        self.psd = {}
        self.pac = {}
        self.one_grp = None
        self.nseg = None

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
        self.chunk['segment'] = FormRadio('by longest &run')
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

        ftypes = ['none', 'butter', 'cheby1', 'cheby2', 'ellip', 'bessel',
                  'diff']
        
        self.trans['bp'] = tbp = {}
        self.trans['bandpass'] = FormMenu(ftypes)
        tbp['order'] = QLabel('Order'), FormSpin(3, 0, 8, 1)
        tbp['f1'] = QLabel('Lowcut (Hz)'), FormFloat()
        tbp['f2'] = QLabel('Highcut (Hz)'), FormFloat()
        
        self.trans['n1'] = tn1 = {}
        self.trans['notch1'] = FormMenu(ftypes)
        tn1['order'] = QLabel('Order'), FormSpin(3, 0, 8, 1)
        tn1['cf'] = QLabel('Centre (Hz)'), FormFloat()
        tn1['bw'] = QLabel('Bandwidth (Hz)'), FormFloat()
        
        self.trans['n2'] = tn2 = {}
        self.trans['notch2'] = FormMenu(ftypes)
        tn2['order'] = QLabel('Order'), FormSpin(3, 0, 8, 1)
        tn2['cf'] = QLabel('Centre (Hz)'), FormFloat()
        tn2['bw'] = QLabel('Bandwidth (Hz)'), FormFloat()
        
        form = QFormLayout(box2)
        form.addRow('Bandpass', self.trans['bandpass'])
        form.addRow(*tbp['order'])
        form.addRow(*tbp['f1'])
        form.addRow(*tbp['f2'])
        form.addRow('Notch 1', self.trans['notch1'])
        form.addRow(*tn1['order'])
        form.addRow(*tn1['cf'])
        form.addRow(*tn1['bw'])
        form.addRow('Notch 2', self.trans['notch2'])
        form.addRow(*tn2['order'])
        form.addRow(*tn2['cf'])
        form.addRow(*tn2['bw'])
        
        self.trans['button'] = {}
        tb = self.trans['button']
        tb['none'] = FormRadio('&None')
        tb['butter'] = FormRadio('&Butterworth filter')
        tb['cheby'] = FormRadio('&Chebyshev type 2 filter')

        self.trans['filt'] = {}
        filt = self.trans['filt']
        filt['order'] = QLabel('Order'), FormInt(default=3)
        filt['f1'] = QLabel('Lowcut (Hz)'), FormFloat()
        filt['f2'] = QLabel('Highcut (Hz)'), FormFloat()
        filt['notch1_centre'] = QLabel('Centre (Hz)'), FormFloat()
        filt['notch1_bandw'] = QLabel('Bandwidth (Hz)'), FormFloat()        
        filt['notch2_centre'] = QLabel('Centre (Hz)'), FormFloat()
        filt['notch2_bandw'] = QLabel('Bandwidth (Hz)'), FormFloat()
        filt['bandpass_l'] = QLabel('Bandpass'), None
        filt['notch1_l'] = QLabel('Notch 1'), None
        filt['notch2_l'] = QLabel('Notch 2'), None

#==============================================================================
#         flayout = QFormLayout()
#         box2.setLayout(flayout)
#         flayout.addRow(tb['none'])
#         flayout.addRow(tb['butter'])
#         flayout.addRow(tb['cheby'])
#         flayout.addRow(*filt['order'])
#         flayout.addRow(filt['bandpass_l'][0])
#         flayout.addRow(*filt['f1'])
#         flayout.addRow(*filt['f2'])
#         flayout.addRow(filt['notch1_l'][0])
#         flayout.addRow(*filt['notch1_centre'])
#         flayout.addRow(*filt['notch1_bandw'])        
#         flayout.addRow(filt['notch2_l'][0])
#         flayout.addRow(*filt['notch2_centre'])
#         flayout.addRow(*filt['notch2_bandw'])
#==============================================================================
        
        """ ------ N_SEG ------ """
        
        box_nseg = QGroupBox('Info')
        
        self.show_nseg = QLabel('')
        
        form = QFormLayout(box_nseg)
        form.addRow(self.show_nseg)

        """ ------ FREQUENCY ------ """

        tab_freq = QWidget()

        self.frequency = {}
        freq = self.frequency

        freq['freq_on'] = FormBool('Compute frequency domain')
        freq['plot_on'] = FormBool('Plot mean spectrum')

        freq['box_param'] = QGroupBox('Parameters')

        freq['scaling'] = FormMenu(['power', 'energy', 'fieldtrip', 'chronux'])
        freq['taper'] = FormMenu(['boxcar', 'hann', 'dpss', 'triang',
            'blackman', 'hamming', 'bartlett', 'flattop', 'parzen', 'bohman',
                'blackmanharris', 'nuttall', 'barthann'])
        freq['detrend'] = FormMenu(['none', 'constant', 'linear'])
        freq['welch_on'] = FormBool("Time-averaged")

        flayout = QFormLayout(freq['box_param'])
        flayout.addRow('Scaling', freq['scaling'])
        flayout.addRow('Taper', freq['taper'])
        flayout.addRow('Detrend', freq['detrend'])
        flayout.addRow(freq['welch_on'])

        freq['box_welch'] = QGroupBox("Time averaging")

        freq['duration'] = FormFloat(1)
        freq['overlap'] = FormRadio('Overlap (0-1)')
        freq['step'] = FormRadio('Step (sec)')
        freq['overlap_val'] = QDoubleSpinBox()
        freq['overlap_val'].setRange(0, 1)
        freq['overlap_val'].setSingleStep(0.1)
        freq['overlap_val'].setValue(0.5)
        freq['step_val'] = FormFloat(0.5)

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
        freq['hbw_val'] = FormSpin(3, 0)
        freq['nhbw_val'] = FormSpin(min_val=0)

        glayout = QGridLayout()
        freq['box_mtap'].setLayout(glayout)
        glayout.addWidget(freq['hbw'], 0, 0)
        glayout.addWidget(freq['nhbw'], 1, 0)
        glayout.addWidget(freq['hbw_val'], 0, 1)
        glayout.addWidget(freq['nhbw_val'], 1, 1)

        freq['box_output'] = QGroupBox('Output')

        freq['spectrald'] = FormRadio('Spectral density')
        freq['complex'] = FormRadio('Complex')
        freq['sides'] = FormSpin(min_val=1, max_val=2)

        glayout = QGridLayout(freq['box_output'])
        glayout.addWidget(freq['spectrald'], 0, 0, 1, 3)
        glayout.addWidget(freq['complex'], 1, 0, 1, 3)
        glayout.addWidget(QLabel('      '), 2, 0)
        glayout.addWidget(QLabel('Side(s)'), 2, 1)
        glayout.addWidget(freq['sides'], 2, 2)

        freq['box_nfft'] = QGroupBox('FFT Length')
        
        freq['nfft_seg'] = FormRadio('Same as segment')
        freq['nfft_fixed'] = FormRadio('Fixed:')
        freq['nfft_fixed_val'] = FormInt()
        freq['nfft_zeropad'] = FormRadio('Zero-pad to longest segment')
        
        glayout = QGridLayout(freq['box_nfft'])
        glayout.addWidget(freq['nfft_seg'], 0, 0, 1, 2)
        glayout.addWidget(freq['nfft_fixed'], 1, 0)
        glayout.addWidget(freq['nfft_fixed_val'], 1, 1)
        glayout.addWidget(freq['nfft_zeropad'], 2, 0, 1, 2)

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

        freq['box_plot'] = QGroupBox('Plot')

        freq['title'] = FormStr()
        freq['axis_scale'] = FormMenu(['log y-axis', 'log both axes',
                                        'linear'])
        freq['min_x_axis'] = FormFloat(0.5)
        freq['max_x_axis'] = FormFloat()

        flayout = QFormLayout(freq['box_plot'])
        flayout.addRow(freq['plot_on'])
        flayout.addRow('Title:',
                       freq['title'])
#==============================================================================
#         flayout.addRow('Axis scaling',
#                        freq['axis_scale'])
#==============================================================================
#==============================================================================
#         flayout.addRow('Lower limit (Hz)',
#                        freq['min_x_axis'])
#         flayout.addRow('Upper limit (Hz)',
#                        freq['max_x_axis'])
#==============================================================================

        glayout = QGridLayout()
        glayout.addWidget(freq['box_param'], 0, 0)
        glayout.addWidget(freq['box_welch'], 0, 1)
        glayout.addWidget(freq['box_nfft'], 1, 0)
        glayout.addWidget(freq['box_mtap'], 1, 1)
        glayout.addWidget(freq['box_output'], 2, 0)
        glayout.addWidget(freq['box_norm'], 2, 1, 3, 1)
        # glayout.addWidget(freq['box_plot'], 2, 1)

        vlayout = QVBoxLayout(tab_freq)
        vlayout.addWidget(freq['freq_on'])
        vlayout.addWidget(freq['plot_on'])
        vlayout.addLayout(glayout)
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
            pac['surro_norm'] = FormMenu(pac_norm)
            pac['surro'] = {}
            sur = pac['surro']
            sur['nperm'] = QLabel('Number of surrogates'), FormInt(default=200)
            sur['nblocks'] = (QLabel('Number of amplitude blocks'),
                              FormInt(default=2))
            sur['pval'] = FormBool('Get p-values'), None
            sur['save_surro'] = FormBool('Save surrogate data'), None

            flayout = QFormLayout(pac['box_surro'])
            flayout.addRow(pac['surro_method'])
            flayout.addRow(pac['surro_norm'])
            flayout.addRow(*sur['nperm'])
            flayout.addRow(*sur['nblocks'])
            flayout.addRow(sur['pval'][0])
            flayout.addRow(sur['save_surro'][0])

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
        eg['density_per'] = FormFloat(30.0)
        eg['all_local'] = FormBool('All')
        eg['all_local_prep'] = FormBool('')

        ev['local'] = {}
        el = ev['local']
        el['dur'] = FormBool('Duration (sec)'), FormBool('')
        el['minamp'] = FormBool('Min. amplitude (uV)'), FormBool('')
        el['maxamp'] = FormBool('Max. amplitude (uV)'), FormBool('')
        el['ptp'] = FormBool('Peak-to-peak amplitude (uV)'), FormBool('')
        el['rms'] = FormBool('RMS (uV)'), FormBool('')
        el['power'] = FormBool('Power (uV**2)'), FormBool('')
        el['energy'] = FormBool('Energy (uV**2 / s)'), FormBool('')
        el['peakpf'] = FormBool('Peak power frequency (Hz)'), FormBool('')
        el['peakef'] = FormBool('Peak energy frequency (Hz)'), FormBool('')

        ev['f1'] = FormFloat()
        ev['f2'] = FormFloat()
        
        ev['sw'] = {}
        ev['sw']['invert'] = FormBool('Inverted (peak-then-trough)')
        ev['sw']['prep'] = FormBool('Pre-process')
        ev['sw']['avg_slope'] = FormBool('Average slopes (uV/s)')
        ev['sw']['max_slope'] = FormBool('Max. slopes (uV/s**2)')
        #ev['slope'] = []
        #for i in range(10):
        #    ev['slope'].append(FormBool(''))

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
        grid2.addWidget(el['power'][0], 7, 0)
        grid2.addWidget(el['power'][1], 7, 2)
        grid2.addWidget(el['energy'][0], 8, 0)
        grid2.addWidget(el['energy'][1], 8, 2)
        grid2.addWidget(el['peakpf'][0], 9, 0)
        grid2.addWidget(el['peakpf'][1], 9, 2)
        grid2.addWidget(el['peakef'][0], 10, 0)
        grid2.addWidget(el['peakef'][1], 10, 2)

        ev['band_box'] = QGroupBox('Band of interest')
        
        form = QFormLayout(ev['band_box'])
        form.addRow('Lowcut (Hz)', ev['f1'])
        form.addRow('Highcut (Hz)', ev['f2'])
        
        box_sw = QGroupBox('Slow wave')

        form = QFormLayout(box_sw)
        form.addRow(ev['sw']['avg_slope'])
        form.addRow(ev['sw']['max_slope'])
        form.addRow(ev['sw']['prep'])
        form.addRow(ev['sw']['invert'])
        
#==============================================================================
#         grid3 = QGridLayout(box_sw)
#         grid3.addWidget(ev['sw']['invert'], 0, 0, 1, 2)
#         grid3.addWidget(ev['sw']['prep'], 1, 0, 1, 2)
#         grid3.addWidget(ev['sw']['all_slope'], 2, 0, 1, 2)
#         grid3.addWidget(QLabel('Quadrant'), 3, 0)
#         grid3.addWidget(QLabel('Average\nslope (uV/s)'), 3, 1)
#         grid3.addWidget(QLabel('Maximum\nslope (uV/s)'), 3, 2)
#         grid3.addWidget(QLabel('1'), 4, 0)
#         grid3.addWidget(QLabel('2'), 5, 0)
#         grid3.addWidget(QLabel('3'), 6, 0)
#         grid3.addWidget(QLabel('4'), 7, 0)
#         grid3.addWidget(QLabel('2 & 3'), 8, 0)
#         for i,w in enumerate(ev['slope']):
#             x = floor(i/5)
#             grid3.addWidget(w, i - 5 * x + 4, x + 1)
#==============================================================================

        grid = QGridLayout()
        grid.addWidget(box_global, 0, 0)
        grid.addWidget(ev['band_box'], 0, 1)
        grid.addWidget(box_local, 1, 0, 1, 2)
        grid.addWidget(box_sw, 2, 0, 1, 2)
        
        vlayout = QVBoxLayout(tab_evt)
        vlayout.addLayout(grid)
        #vlayout.addWidget(box_global)
        #vlayout.addWidget(box_local)
        #vlayout.addWidget(ev['band_box'])
        #vlayout.addWidget(box_sw)
        vlayout.addStretch(1)

        """ ------ TRIGGERS ------ """

        for button in self.chunk.values():
            button.toggled.connect(self.toggle_buttons)
            button.toggled.connect(self.toggle_freq)

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
        
        self.epoch_dur.editingFinished.connect(self.update_nseg)
        self.min_dur.editingFinished.connect(self.update_nseg)
        self.reject_epoch.connect(self.update_nseg)
        self.reject_event.connect(self.update_nseg)
        
        for box in self.cat.values():
            box.connect(self.update_nseg)

        self.trans['bandpass'].connect(self.toggle_buttons)
        self.trans['notch1'].connect(self.toggle_buttons)
        self.trans['notch2'].connect(self.toggle_buttons)
        
        freq['freq_on'].connect(self.toggle_freq)
        freq['plot_on'].connect(self.toggle_freq)
        freq['taper'].connect(self.toggle_freq)
        freq['welch_on'].connect(self.toggle_freq)
        freq['complex'].connect(self.toggle_freq)
        freq['overlap'].connect(self.toggle_freq)
        freq['hbw'].connect(self.toggle_freq)
        freq['norm'].connect(self.toggle_freq)
        freq['nfft_fixed'].connect(self.toggle_freq)
        freq['nfft_zeropad'].connect(self.toggle_freq)

        if Pac is not None:
            pac['pac_on'].connect(self.toggle_pac)
            pac['hilbert_on'].toggled.connect(self.toggle_pac)
            pac['wavelet_on'].toggled.connect(self.toggle_pac)
            pac['metric'].connect(self.toggle_pac)
            pac['surro_method'].connect(self.toggle_pac)
            pac['surro_norm'].connect(self.toggle_pac)

        eg['density'].connect(self.toggle_buttons)
        eg['all_local'].clicked.connect(self.check_all_local)
        eg['all_local_prep'].clicked.connect(self.check_all_local_prep)
        for button in el.values():
            button[0].clicked.connect(self.uncheck_all_local)
            button[1].clicked.connect(self.uncheck_all_local)
        #ev['sw']['all_slope'].connect(self.check_all_slopes)
        ev['sw']['avg_slope'].connect(self.toggle_buttons)
        ev['sw']['max_slope'].connect(self.toggle_buttons)

        bbox.clicked.connect(self.button_clicked)

        """ ------ SET DEFAULTS ------ """

        self.evt_chan_only.setChecked(True)
        self.lock_to_staging.setChecked(True)
        self.chunk['epoch'].setChecked(True)
        self.reject_epoch.setChecked(True)
        self.trans['button']['none'].setChecked(True)

        freq['plot_on'].setEnabled(False)
        freq['box_param'].setEnabled(False)
        freq['box_welch'].setEnabled(False)
        freq['box_nfft'].setEnabled(False)
        freq['box_mtap'].setEnabled(False)
        freq['box_output'].setEnabled(False)
        freq['box_norm'].setEnabled(False)
        # freq['box_plot'].setEnabled(False)
        freq['welch_on'].set_value(True)
        freq['nfft_seg'].setChecked(True)
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
        vlayout2.addWidget(box_nseg)
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
            surro = self.pac['surro_method']
            surro.model().item(1).setEnabled(epoch_on)
            if surro.get_value() == 'Swap phase/amplitude across trials':
                surro.set_value('No surrogates')
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

#==============================================================================
#         filter_on = not self.trans['button']['none'].isChecked()
#         for button in self.trans['filt'].values():
#             button[0].setEnabled(filter_on)
#             if button[1] is not None:
#                 button[1].setEnabled(filter_on)
#==============================================================================

        bandpass_on = self.trans['bandpass'].get_value() != 'none'
        for w in self.trans['bp'].values():
            w[0].setEnabled(bandpass_on)
            w[1].setEnabled(bandpass_on)
            
        notch1_on = self.trans['notch1'].get_value() != 'none'
        for w in self.trans['n1'].values():
            w[0].setEnabled(notch1_on)
            w[1].setEnabled(notch1_on)

        notch2_on = self.trans['notch2'].get_value() != 'none'
        for w in self.trans['n2'].values():
            w[0].setEnabled(notch2_on)
            w[1].setEnabled(notch2_on)

        density_on = self.event['global']['density'].isChecked()
        self.event['global']['density_per'].setEnabled(density_on)

        for buttons in self.event['local'].values():
            checked = buttons[0].isChecked()
            buttons[1].setEnabled(checked)
            if not checked:
                buttons[1].setChecked(False)
        
        el = self.event['local']
        ev_psd_on = asarray([x.get_value() for x in [el['power'][0], 
                             el['energy'][0], el['peakpf'][0], 
                             el['peakef'][0]]]).any()
        self.event['band_box'].setEnabled(ev_psd_on)
        
        sw = self.event['sw']
        slope_on = sw['avg_slope'].get_value() or sw['max_slope'].get_value()
        sw['prep'].setEnabled(slope_on)
        sw['invert'].setEnabled(slope_on)
        
        self.update_nseg()

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
            
        self.update_nseg()

    def toggle_freq(self):
        """Enable and disable frequency domain options."""
        freq = self.frequency

        freq_on = freq['freq_on'].get_value()
        freq['box_param'].setEnabled(freq_on)
        freq['box_output'].setEnabled(freq_on)
        freq['box_norm'].setEnabled(freq_on)
        freq['box_nfft'].setEnabled(freq_on)

        welch_on = freq['welch_on'].get_value() and freq_on
        freq['box_welch'].setEnabled(welch_on)

        # plot_on = freq['plot_on'].get_value()
        # freq['box_plot'].setEnabled(plot_on)

        if welch_on:
            overlap_on = freq['overlap'].isChecked()
            freq['overlap_val'].setEnabled(overlap_on)
            freq['step_val'].setEnabled(not overlap_on)
            freq['box_output'].setEnabled(not welch_on)
            freq['spectrald'].setChecked(True)

        nfft_fixed_on = freq['nfft_fixed'].isChecked()
        zeropad_on = freq['nfft_zeropad'].isChecked()
        freq['nfft_fixed_val'].setEnabled(nfft_fixed_on)

        epoch_on = self.chunk['epoch'].isChecked()
        rectangular = welch_on or epoch_on or zeropad_on or nfft_fixed_on or \
                        (self.nseg == 1)
        freq['plot_on'].setEnabled(freq_on and rectangular)
        if not freq['plot_on'].isEnabled():
            freq['plot_on'].set_value(False) 
        
        dpss_on = freq['taper'].get_value() == 'dpss'
        freq['box_mtap'].setEnabled(dpss_on)

        if dpss_on:
            hbw_on = freq['hbw'].isChecked()
            freq['hbw_val'].setEnabled(hbw_on)
            freq['nhbw_val'].setEnabled(not hbw_on)

        complex_on = freq['complex'].isChecked()
        freq['sides'].setEnabled(complex_on)
        if complex_on:
            freq['welch_on'].setEnabled(False)
            freq['welch_on'].set_value(False)
        else:
            freq['welch_on'].setEnabled(True)

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

            pac = self.pac
            hilb_on = pac['hilbert_on'].isChecked()
            wav_on = pac['wavelet_on'].isChecked()
            for button in pac['hilbert'].values():
                button[0].setEnabled(hilb_on)
                if button[1] is not None:
                    button[1].setEnabled(hilb_on)
            pac['wav_width'][0].setEnabled(wav_on)
            pac['wav_width'][1].setEnabled(wav_on)

            if pac['metric'].get_value() in [
                    'Kullback-Leibler Distance',
                    'Heights ratio']:
                pac['nbin'][0].setEnabled(True)
                pac['nbin'][1].setEnabled(True)
            else:
                pac['nbin'][0].setEnabled(False)
                pac['nbin'][1].setEnabled(False)

            if pac['metric'] == 'ndPac':
                for button in pac['surro'].values():
                    button[0].setEnabled(False)
                    if button[1] is not None:
                        button[1].setEnabled(False)
                pac['surro']['pval'].setEnabled(True)

            ndpac_on = pac['metric'].get_value() == 'ndPac'
            surro_on = logical_and(pac['surro_method'].get_value() != ''
                                       'No surrogates', not ndpac_on)
            norm_on = pac['surro_norm'].get_value() != 'No normalization'
            blocks_on = 'across time' in pac['surro_method'].get_value()
            pac['surro_method'].setEnabled(not ndpac_on)
            for button in pac['surro'].values():
                button[0].setEnabled(surro_on and norm_on)
                if button[1] is not None:
                    button[1].setEnabled(surro_on and norm_on)
            pac['surro']['nblocks'][0].setEnabled(blocks_on)
            pac['surro']['nblocks'][1].setEnabled(blocks_on)
            if ndpac_on:
                pac['surro_method'].set_value('No surrogates')
                pac['surro']['pval'].setEnabled(True)

    def update_nseg(self):
        """Update the number of segments, displayed in the dialog."""
        self.nseg = None
        if self.one_grp:        
            bundles = self.get_bundles()
            
            if bundles is not None:
                self.nseg = len(bundles)
                self.show_nseg.setText('Number of segments: ' + str(self.nseg))
                
            else:
                self.show_nseg.setText('No valid segments')
                
        self.toggle_freq()
    
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

#==============================================================================
#     def check_all_slopes(self):
#         """Check and uncheck slope options"""
#         slopes_checked = self.event['sw']['all_slope'].get_value()
#         for button in self.event['slope']:
#             button.setChecked(slopes_checked)
#==============================================================================

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            # File location
            filename = self.filename
            if filename is None:
                return
            
            # Which analyses?
            freq_on = self.frequency['freq_on'].get_value()
            freq_plot_on = self.frequency['plot_on'].get_value()
            
            if Pac is not None:
                pac_on = self.pac['pac_on'].get_value()
            else:
                pac_on = False
            
            #if not (freq_on or pac_on):
            #    return

            # Fetch signal            
            self.update_nseg
            self.read_data()

            # Frequency domain
            if freq_on:
                freq_filename = splitext(filename)[0] + '_freq.p'
                xfreq = self.compute_freq()

                with open(freq_filename, 'wb') as f:
                    dump(xfreq, f)
                    
                n_freq_bins = [x['data']()[0].shape for x in xfreq]
                
                if all(x == n_freq_bins[0] for x in n_freq_bins):
                    as_matrix = asarray(
                            [y for x in xfreq for y in x['data']()[0]])
                    desc = get_descriptives(as_matrix)
                    self.export_freq(xfreq, desc)
                    
                    if freq_plot_on:
                        x = list(xfreq[0]['data'].axis['freq'][0])
                        y = desc['mean']
                        self.plot_freq(x, y, title=self.title)

            # PAC
            if pac_on:
                xpac, fpha, famp = self.compute_pac()
                pac_filename = splitext(filename)[0] + '_pac.p'

                with open(pac_filename, 'wb') as f:
                    dump(xpac, f)

                as_matrix = asarray(
                        [ravel(chan['data'][x,:,:]) for chan in xpac.values() \
                         for x in range(chan['data'].shape[0])])
                desc = get_descriptives(as_matrix)
                self.export_pac(xpac, fpha, famp, desc)
                
            # Events
            loc_prep = [v[1].get_value() for v in self.event['local'].values()]
            slope_prep = self.event['sw']['prep'].get_value()
            
            if slope_prep or asarray(loc_prep).any():
                self.transform_data()
            
            glob, loc = self.compute_evt_params()
            
            self.export_evt_params(glob, loc)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

    def get_bundles(self):
        """Use information from user to find relevant data and create dicts 
        (bundles) for each segment to be analyzed, complete with info about
        stage, cycle, channel, event type"""
        # Chunking
        chunk = {k: v.isChecked() for k, v in self.chunk.items()}
        epoch_dur = self.epoch_dur.get_value()

        # Which event type(s)
        if chunk['event']:
            evt_type = self.idx_evt_type.selectedItems()
            if not evt_type:
                return
            else:
                evt_type = [x.text() for x in evt_type]
        else:
            evt_type = None

        # Which channel(s)
        self.chan = self.get_channels()
        if not self.chan:
            return
        chan_full = [i + ' (' + self.idx_group.currentText() + ''
                       ')' for i in self.chan]

        # Which cycle(s)
        cycle = self.cycle = self.get_cycles()

        # Which stage(s)
        stage = self.idx_stage.selectedItems()
        if not stage:
            stage = self.stage = None
        else:
            stage = self.stage = [
                    x.text() for x in self.idx_stage.selectedItems()]
        lg.info('Stages from GUI: ' + str(stage))

        # Concatenation
        cat = {k: v.get_value() for k, v in self.cat.items()}
        lg.info('Cat: ' + str(cat))
        self.concat_chan = cat['chan']
        cat = (int(cat['cycle']), int(cat['stage']),
               int(cat['discontinuous']), int(cat['evt_type']))

        # Other options
        lock_to_staging = self.lock_to_staging.get_value()
        reject_epoch = self.reject_epoch.get_value()
        reject_artf = self.reject_event.get_value()
        # trans = {k: v.get_value() for k, v in self.trans['button'].items()}
        # filt = {k: v[1].get_value() for k, v in \
        #         self.trans['filt'].items() if v[1] is not None}

        # Get times
        lg.info('Getting ' + ', '.join((str(evt_type), str(stage),
                                       str(cycle), str(chan_full),
                                       str(reject_epoch))))
        bundles = get_times(self.parent.notes.annot, evt_type=evt_type,
                            stage=stage, cycle=cycle, chan=chan_full,
                            exclude=reject_epoch)
        lg.info('Get times: ' + str(len(bundles)))            

        # Remove artefacts
        if reject_artf and bundles:
            for bund in bundles:
                bund['times'] = remove_artf_evts(bund['times'],
                                                self.parent.notes.annot,
                                                min_dur=0)
            lg.info('After remove artf evts: ' + str(len(bundles)))

        # Minimum duration
        if bundles:
            bundles = longer_than(bundles, self.min_dur.get_value())
            lg.info('Longer than: ' + str(len(bundles)))

        # Divide bundles into segments to be analyzed
        if bundles:
            
            if chunk['epoch']:

                if lock_to_staging:
                    bundles = divide_bundles(bundles)
                    lg.info('Divided ' + str(len(bundles)))

                else:
                    bundles = find_intervals(bundles, epoch_dur)
                    lg.info('Find intervals: ' + str(len(bundles)))
                    
            else:
                lg.info('Preparing concatenation: ' + str(cat))
                bundles = _concat(bundles, cat)
                lg.info('After concat: ' + str(len(bundles)))                

        # Generate title for summary plot
        self.title = self.make_title(chan_full, cycle, stage, evt_type)
        
        return bundles
    
    def read_data(self):
        """Read data for analysis."""
        bundles = self.get_bundles()
        
        if not bundles:
            self.parent.statusBar().showMessage('No valid signal found.')
            self.accept()
            return
        
        dataset = self.parent.info.dataset
        chan_to_read = self.chan + self.one_grp['ref_chan']
        evt_chan_only = self.evt_chan_only.get_value()

        data = dataset.read_data(chan=chan_to_read)

        max_s_freq = self.parent.value('max_s_freq')
        if data.s_freq > max_s_freq:
            q = int(data.s_freq / max_s_freq)
            lg.debug('Decimate (no low-pass filter) at ' + str(q))

            data.data[0] = data.data[0][:, slice(None, None, q)]
            data.axis['time'][0] = data.axis['time'][0][slice(None, None, q)]
            data.s_freq = int(data.s_freq / q)

        self.data = _create_data_to_analyze(data, self.chan, self.one_grp,
                                            bundles=bundles,
                                            concat_chan=self.concat_chan,
                                            evt_chan_only=evt_chan_only,
                                            parent=self)

    def transform_data(self):
        """Apply pre-processing transformation to data, and add it to data 
        dict."""
        trans = self.trans
        bandpass = trans['bandpass'].get_value()
        notch1 = trans['notch1'].get_value()
        notch2 = trans['notch2'].get_value()
        
        for seg in self.data:
            dat = seg['data']
        
            if bandpass != 'none':
                order = trans['bp']['order'][1].get_value()
                f1 = trans['bp']['f1'][1].get_value()
                f2 = trans['bp']['f2'][1].get_value()
                
                if f1 == '':
                    f1 = None
                if f2 == '':
                    f2 = None
                    
                dat = filter_(dat, low_cut=f1, high_cut=f2, order=order,
                              ftype=bandpass)
            
            if notch1 != 'none':
                order = trans['n1']['order'][1].get_value()
                cf = trans['n1']['cf'][1].get_value()
                hbw = trans['n1']['bw'][1].get_value() / 2.0
                lo_pass = cf - hbw
                hi_pass = cf + hbw
                dat = filter_(dat, low_cut=hi_pass, order=order, ftype=notch1)
                dat = filter_(dat, high_cut=lo_pass, order=order, ftype=notch1)
        
            if notch2 != 'none':
                order = trans['n2']['order'][1].get_value()
                cf = trans['n2']['cf'][1].get_value()
                hbw = trans['n2']['bw'][1].get_value() / 2.0
                lo_pass = cf - hbw
                hi_pass = cf + hbw
                dat = filter_(dat, low_cut=hi_pass, order=order, ftype=notch1)
                dat = filter_(dat, high_cut=lo_pass, order=order, ftype=notch1) 
                
            seg['trans_data'] = dat
    
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
        progress = QProgressDialog('Computing frequency', 'Abort',
                                   0, len(self.data), self)
        progress.setWindowModality(Qt.ApplicationModal)

        freq = self.frequency
        scaling = freq['scaling'].get_value()
        sides = freq['sides'].get_value()
        taper = freq['taper'].get_value()
        halfbandwidth = freq['hbw_val'].get_value()
        NW = freq['nhbw_val'].get_value()
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
        
        if freq['nfft_fixed'].isChecked():
            n_smp = int(freq['nfft_fixed_val'].get_value())
        elif freq['nfft_zeropad'].isChecked():
            n_smp = max([x['data'].number_of('time') for x in self.data])
        elif freq['nfft_seg'].isChecked():
            n_smp = None

        lg.info(' '.join(['Freq settings:', output, scaling, 'sides:',
                         str(sides), taper, 'hbw:', str(halfbandwidth), 'NW:',
                         str(NW), 'dur:', str(duration), 'overlap:',
                         str(overlap), 'step:', str(step), 'detrend:',
                         str(detrend), 'n_smp:', str(n_smp)]))

        xfreq = []
        for i, seg in enumerate(self.data):
            progress.setValue(i)
            new_seg = dict(seg)
            data = seg['data']
            timeline = seg['data'].axis['time'][0]
            new_seg['times'] = timeline[0], timeline[-1]
            new_seg['duration'] = len(timeline) / data.s_freq

            Sxx = frequency(data, output=output, scaling=scaling, sides=sides,
                            taper=taper, halfbandwidth=halfbandwidth, NW=NW,
                            duration=duration, overlap=overlap, step=step,
                            detrend=detrend, n_smp=n_smp)
            new_seg['data'] = Sxx
            xfreq.append(new_seg)

            if progress.wasCanceled():
                break

        progress.setValue(i+1)

        return xfreq

    def export_freq(self, xfreq, desc):
        """Write frequency analysis data to CSV."""
        filename = splitext(self.filename)[0] + '_freq.csv'

        heading_row_1 = ['Segment index',
                       'Start time',
                       'End time',
                       'Duration',
#                       'Stitches',
                       'Stage',
                       'Cycle',
                       'Event type',
                       'Channel',
                       ]
        spacer = [''] * (len(heading_row_1) - 1)
        freq = list(xfreq[0]['data'].axis['freq'][0])

        with open(filename, 'w', newline='') as f:
            lg.info('Writing to' + str(filename))
            csv_file = writer(f)
            csv_file.writerow(heading_row_1 + freq)
            csv_file.writerow(['Mean'] + spacer + list(desc['mean']))
            csv_file.writerow(['SD'] + spacer + list(desc['sd']))
            csv_file.writerow(['Mean of ln'] + spacer + list(desc['mean_log']))
            csv_file.writerow(['SD of ln'] + spacer + list(desc['sd_log']))
            idx = 0

            for seg in xfreq:

                for chan in seg['data'].axis['chan'][0]:
                    idx += 1
                    data_row = list(seg['data'](chan=chan)[0])
                    csv_file.writerow([idx,
                                       seg['times'][0],
                                       seg['times'][1],
                                       seg['duration'],
#                                       seg['n_stitch'],
                                       seg['stage'],
                                       seg['cycle'][2],
                                       seg['name'],
                                       chan,
                                       ] + data_row)

    def plot_freq(self, x, y, title=''):
        """Plot mean frequency spectrum and display in dialog.

        Parameters
        ----------
        x : ndarray
            vector with frequencies
        y : ndarray
            vector with amplitudes
        """
        freq = self.frequency
        scaling = freq['scaling'].get_value()
        
#==============================================================================
#         title = freq['title'].get_value()
#         log = freq['axis_scale'].get_value()
#         xlim = freq['min_x_axis'].get_value(), freq['max_x_axis'].get_value()
#
#         idx_low = (abs(x - xlim[0])).argmin()
#
#         if xlim[1] == 0:
#             idx_high = None
#         else:
#             idx_high = (abs(x - xlim[1])).argmin()
#
#         lg.info('limits: ' + str(idx_low) + ' ' + str(idx_high))
#==============================================================================

        if freq['complex'].get_value():
            ylabel = 'Amplitude (uV)'
        elif 'power' == scaling:
            ylabel = 'Power spectral density (uV ** 2 / Hz)'
        elif 'energy' == scaling:
            ylabel = 'Energy spectral density (uV ** 2)'

        self.parent.plot_dialog.canvas.plot(x, y, title, ylabel,
                                            #log=log,
                                            #idx_lim=(idx_low, idx_high)
                                            )
        self.parent.show_plot_dialog()

    def compute_pac(self):
        """Compute phase-amplitude coupling values from data."""
        progress = QProgressDialog('Computing PAC', 'Abort',
                                   0, len(self.data), self)
        progress.setWindowModality(Qt.ApplicationModal)

        pac = self.pac
        idpac = (pac['metric'].currentIndex() + 1,
                 pac['surro_method'].currentIndex(),
                 pac['surro_norm'].currentIndex())
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

        lg.info(' '.join([str(x) for x in ['Instantiating PAC:', 'idpac:',
                          idpac, 'fpha:', fpha, 'famp:', famp,  'dcomplex:',
                          dcomplex, 'filt:', filt, 'cycle:', cycle,
                          'filtorder:', filtorder, 'width:', width,
                          'nbins:', nbins, 'nblocks:', nblocks]]))
        p = Pac(idpac=idpac, fpha=fpha, famp=famp, dcomplex=dcomplex,
                filt=filt, cycle=cycle, filtorder=filtorder, width=width,
                nbins=nbins, nblocks=nblocks)

        nperm = self.pac['surro']['nperm'][1].get_value()
        optimize = self.pac['optimize'].get_value()
        get_pval = self.pac['surro']['pval'][0].get_value()
        lg.info('get_pval is ' + str(get_pval is True))
        get_surro = self.pac['surro']['save_surro'][0].get_value()
        njobs = self.pac['njobs'].get_value()

        if optimize == 'True':
            optimize = True
        elif optimize == 'False':
            optimize = False

        xpac = {}

        all_chan = sorted(set(
                [x for y in self.data for x in y['data'].axis['chan'][0]]))

        counter = 0
        for chan in all_chan:
            batch = []
            batch_dat = []

            for i, j in enumerate(self.data):

                if chan in j['data'].axis['chan'][0]:
                    batch.append(j)

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
                progress.setValue(counter)
                counter += 1

                sf = j['data'].s_freq

                if idpac[1] == 1:
                    new_batch_dat = list(batch_dat)
                    new_batch_dat.insert(0, new_batch_dat.pop(i))
                    dat = asarray(new_batch_dat)
                else:
                    dat = j['data'](chan=chan)[0]

                timeline = j['data'].axis['time'][0]
                xpac[chan]['times'].append((timeline[0], timeline[-1]))
                lg.info('Compute PAC on ' + chan + ' ' + str((timeline[0],
                                                              timeline[-1])))
                duration = len(timeline) / sf
                xpac[chan]['duration'].append(duration)
                xpac[chan]['stage'].append(j['stage'])
                xpac[chan]['cycle'].append(j['cycle'])
                xpac[chan]['name'].append(j['name'])

#==============================================================================
#                 lg.info(' '.join([str(x) for x in ['Computing PAC', 'sf:', sf,
#                                   'nperm:', nperm, 'optimize:',
#                                   optimize, 'get_pval:', get_pval,
#                                  'get_surro:', get_surro, 'njobs:', njobs]]))
#==============================================================================
                out = p.filterfit(sf=sf, xpha=dat, xamp=None, axis=1, traxis=0,
                                  nperm=nperm, optimize=optimize,
                                  get_pval=get_pval, get_surro=get_surro,
                                  njobs=njobs)

                if get_pval:

                    if get_surro:
                        (xpac[chan]['data'][i, :, :],
                         xpac[chan]['pval'][i, :, :],
                         xpac[chan]['surro'][i, :, :, :]) = (out[0][:, :, 0],
                             out[1][:, :, 0], out[2][:, :, :, 0])
                    else:
                        (xpac[chan]['data'][i, :, :],
                         xpac[chan]['pval'][i, :, :]) = (out[0][:, :, 0],
                             out[1][:, :, 0])

                elif get_surro:
                    (xpac[chan]['data'][i, :, :],
                     xpac[chan]['surro'][i, :, :, :]) = (out[0][:, :, 0],
                         out[1][:, :, :, 0])

                else:
                    xpac[chan]['data'][i, :, :] = out[:, :, 0]

        progress.setValue(counter)

        return xpac, fpha, famp

    def export_pac(self, xpac, fpha, famp, desc):
        """Write PAC analysis data to CSV."""
        filename = splitext(self.filename)[0] + '_pac.csv'

        heading_row_1 = ['Segment index',
                       'Start time',
                       'End time',
                       'Duration',
#                       'Stitch',
                       'Stage',
                       'Cycle',
                       'Event type',
                       'Channel',
                       ]
        spacer = [''] * (len(heading_row_1) - 1)
        heading_row_2 = []

        for fp in fpha:
            fp_str = str(fp[0]) + '-' + str(fp[1])

            for fa in famp:
                fa_str = str(fa[0]) + '-' + str(fa[1])
                heading_row_2.append(fp_str + '_' + fa_str + '_pac')

        if 'pval' in xpac[list(xpac.keys())[0]].keys():
            heading_row_3 = [x[:-4] + '_pval' for x in heading_row_2]
            heading_row_2.extend(heading_row_3)

        with open(filename, 'w', newline='') as f:
            lg.info('Writing to' + str(filename))
            csv_file = writer(f)
            csv_file.writerow(heading_row_1 + heading_row_2)
            csv_file.writerow(['Mean'] + spacer + list(desc['mean']))
            csv_file.writerow(['SD'] + spacer + list(desc['sd']))
            csv_file.writerow(['Mean of ln'] + spacer + list(desc['mean_log']))
            csv_file.writerow(['SD of ln'] + spacer + list(desc['sd_log']))
            idx = 0

            for chan in xpac.keys():

                for i, j in enumerate(xpac[chan]['times']):
                    idx += 1
                    data_row = list(ravel(xpac[chan]['data'][i, :, :]))

                    pval_row = []
                    if 'pval' in xpac[chan]:
                        pval_row = list(ravel(xpac[chan]['pval'][i, :, :]))

                    csv_file.writerow([idx,
                                       j[0],
                                       j[1],
                                       xpac[chan]['duration'][i],
#                                       seg['n_stitch'],
                                       xpac[chan]['stage'][i],
                                       xpac[chan]['cycle'][i][2],
                                       xpac[chan]['name'][i],
                                       chan,
                                       ] + data_row + pval_row)
            
    def compute_evt_params(self):
        """Compute event parameters."""
        ev = self.event
        glob = {k: v.get_value() for k, v in ev['global'].items()}
        loc = {k: v[0].get_value() for k, v in ev['local'].items()}
        loc_prep = {k: v[1].get_value() for k, v in ev['local'].items()}
        
        avg_slope = ev['sw']['avg_slope'].get_value() 
        max_slope = ev['sw']['max_slope'].get_value()
        slope_prep = ev['sw']['prep'].get_value()
        invert = ev['sw']['invert'].get_value()
        
        glob_out = {}
        loc_out = []
        
        if glob['count']:
            glob_out['count'] = self.nseg
        
        if glob['density']:
            epoch_dur = glob['density_per']
            # get period of interest based on stage and cycle selection
            poi = get_times(self.parent.notes.annot, stage=self.stage, 
                            cycle=self.cycle)
            total_dur = sum([x[1] - x[0] for y in poi for x in y['times']])
            glob_out['density'] = self.nseg / (total_dur / epoch_dur)
        
        for seg in self.data:
            out = dict(seg)
            dat = seg['data']
            timeline = dat.axis['time'][0]
            out['times'] = timeline[0], timeline[-1]
            peakpf_done = False
            peakef_done = False
            
            if loc['dur']:
                out['dur'] = float(dat.number_of('time')) / dat.s_freq
            
            if loc['minamp']:
                dat1 = dat
                if loc_prep['minamp']:
                    dat1 = seg['trans_data']
                out['minamp'] = math(dat1, operator=_amin, axis='time')
            
            if loc['maxamp']:
                dat1 = dat
                if loc_prep['maxamp']:
                    dat1 = seg['trans_data']
                out['maxamp'] = math(dat1, operator=_amax, axis='time')
            
            if loc['ptp']:
                dat1 = dat
                if loc_prep['ptp']:
                    dat1 = seg['trans_data']
                out['ptp'] = math(dat1, operator=_ptp, axis='time')
            
            if loc['rms']:
                dat1 = dat
                if loc_prep['rms']:
                    dat1 = seg['trans_data']
                out['rms'] = math(dat1, operator=(square, _mean, sqrt), 
                   axis='time')
                
            if loc['power'] or loc['energy'] or loc['peakpf']:
                f1, f2 = ev['f1'].get_value(), ev['f2'].get_value()
            
            if loc_prep['power'] or loc_prep['energy'] or loc_prep['peakpf']:
                dat_trans_diff = math(seg['trans_data'], operator=diff, 
                                      axis='time')
                
            if loc['power']:
                out['power'] = {}
                if loc_prep['power']:
                    dat1 = dat_trans_diff
                else:
                    dat1 = math(dat, operator=diff, axis='time')
                Sxx = frequency(dat1)
                sf = Sxx.axis['freq'][0]
                b1 = asarray([abs(x - f1) for x in sf]).argmin()
                b2 = asarray([abs(x - f2) for x in sf]).argmin()
                
                for chan in Sxx.axis['chan'][0]:
                    d = Sxx(chan=chan)[0]
                    out['power'][chan] = sum(d[b1:b2]) # integrating over f
                
                if loc['peakpf'] and (loc_prep['peakpf'] == loc_prep['power']):
                    out['peakpf'] = {}
                    peakpf_done = True
                    
                    for chan in Sxx.axis['chan'][0]:
                        d = Sxx(chan=chan)[0]
                        idx_peak = d[b1:b2].argmax()
                        out['peakpf'][chan] = sf[b1:b2][idx_peak]                                        
                    
            if loc['peakpf'] and not peakpf_done:
                out['peakpf'] = {}
                if loc_prep['peakpf']:
                    dat1 = dat_trans_diff
                else:
                    dat1 = math(dat, operator=diff, axis='time')
                Sxx = frequency(dat1)
                sf = Sxx.axis['freq'][0]
                b1 = asarray([abs(x - f1) for x in sf]).argmin()
                b2 = asarray([abs(x - f2) for x in sf]).argmin()
                
                for chan in Sxx.axis['chan'][0]:
                    d = Sxx(chan=chan)[0]
                    idx_peak = d[b1:b2].argmax()
                    out['peakpf'][chan] = sf[b1:b2][idx_peak]

            if loc['energy']:
                out['energy'] = {}
                if loc_prep['energy']:
                    dat1 = dat_trans_diff
                else:
                    dat1 = math(dat, operator=diff, axis='time')
                Sxx = frequency(dat1, scaling='energy', detrend=None)
                sf = Sxx.axis['freq'][0]
                b1 = asarray([abs(x - f1) for x in sf]).argmin()
                b2 = asarray([abs(x - f2) for x in sf]).argmin()
                
                for chan in Sxx.axis['chan'][0]:
                    d = Sxx(chan=chan)[0]
                    out['energy'][chan] = sum(d[b1:b2]) # integrating over f
                
                if loc['peakef'] and (loc_prep['peakef'] == loc_prep['power']):
                    out['peakef'] = {}
                    peakef_done = True
                    
                    for chan in Sxx.axis['chan'][0]:
                        d = Sxx(chan=chan)[0]
                        idx_peak = d[b1:b2].argmax()
                        out['peakef'][chan] = sf[b1:b2][idx_peak] 
                    
            if loc['peakef'] and not peakef_done:
                out['peakef'] = {}
                if loc_prep['peakef']:
                    dat1 = dat_trans_diff
                else:
                    dat1 = math(dat, operator=diff, axis='time')
                Sxx = frequency(dat1, scaling='energy', detrend=None)  
                sf = Sxx.axis['freq'][0]
                b1 = asarray([abs(x - f1) for x in sf]).argmin()
                b2 = asarray([abs(x - f2) for x in sf]).argmin()
                
                for chan in Sxx.axis['chan'][0]:
                    d = Sxx(chan=chan)[0]
                    idx_peak = d[b1:b2].argmax()
                    out['peakef'][chan] = sf[b1:b2][idx_peak] 
                
            if avg_slope or max_slope:
                out['slope'] = {}
                dat1 = dat
                if slope_prep:
                    dat1 = seg['trans_data']                
                if invert:
                    dat1 = math(dat1, operator=negative, axis='time')
                    
                if avg_slope and max_slope:
                    level = 'all'
                elif avg_slope:
                    level = 'average'
                else:
                    level = 'maximum'
                
                for chan in dat1.axis['chan'][0]:
                    d = dat1(chan=chan)[0]                
                    out['slope'][chan] = get_slopes(d, dat.s_freq, level=level)
            
            loc_out.append(out)
            
        return glob_out, loc_out
        
    def export_evt_params(self, glob, loc, desc=None):
        """Write event analysis data to CSV."""
        filename = splitext(self.filename)[0] + '_evtdat.csv'
        
        heading_row_1 = ['Segment index',
                       'Start time',
                       'End time',
#                       'Stitches',
                       'Stage',
                       'Cycle',
                       'Event type',
                       'Channel']
        spacer = [''] * (len(heading_row_1) - 1)
        
        param_headings_1 = ['Duration (s)',
                            'Min. amplitude (uV)',
                            'Max. amplitude (uV)',
                            'Peak-to-peak amplitude (uV)',
                            'RMS (uV)']
        param_headings_2 = ['Power (uV**2)',
                            'Peak power frequency (Hz)',
                            'Energy (uV**2/s)',
                            'Peak energy frequency (Hz)']
        slope_headings = ['Q1 average slope (uV/s)',
                          'Q2 average slope (uV/s)',
                          'Q3 average slope (uV/s)',
                          'Q4 average slope (uV/s)',
                          'Q23 average slope (uV/s)',
                          'Q1 max. slope (uV/s**2)',
                          'Q2 max. slope (uV/s**2)',
                          'Q3 max. slope (uV/s**2)',
                          'Q4 max. slope (uV/s**2)',
                          'Q23 max. slope (uV/s**2)']
        ordered_params_1 = ['minamp', 'maxamp', 'ptp', 'rms']
        ordered_params_2 = ['power', 'peakpf', 'energy', 'peakef']
        
        idx_params_1 = in1d(ordered_params_1, list(loc[0].keys()))
        sel_params_1 = list(compress(ordered_params_1, idx_params_1))
        heading_row_2 = list(compress(param_headings_1, idx_params_1))
        
        idx_params_2 = in1d(ordered_params_2, list(loc[0].keys()))
        sel_params_2 = list(compress(ordered_params_2, idx_params_2))
        heading_row_3 = list(compress(param_headings_2, idx_params_2))
        
        heading_row_4 = []
        if 'slope' in loc[0].keys():
            if next(iter(loc[0]['slope']))[0]:
                heading_row_4.extend(slope_headings[:5])
            if next(iter(loc[0]['slope']))[1]:
                heading_row_4.extend(slope_headings[5:])
            
        as_matrix_1 = asarray(
                [ravel([ravel(y[x]()[0]) for x in sel_params_1]) for y in loc])
        lg.info('mat1, shape: ' + str(as_matrix_1.shape) + ' ' + str(as_matrix_1))
        as_matrix_2 = asarray([ravel([y[x][chan] for x in sel_params_2 \
                                for chan in y[x]]) for y in loc])
        lg.info('mat2, shape: ' + str(as_matrix_2.shape) + ' ' + str(as_matrix_2))
        as_matrix = hstack((as_matrix_1, as_matrix_2))
        lg.info('mat, shape: ' + str(as_matrix.shape) + ' ' + str(as_matrix))
        if 'dur' in loc[0].keys():
            as_matrix_0 = reshape(asarray([x['dur'] for x in loc]), 
                                  (len(loc), 1))
            lg.info('mat0, shape: ' + str(as_matrix_0.shape) + ' ' + str(as_matrix_0))
            as_matrix = hstack((as_matrix_0, as_matrix))
        if 'slope' in loc[0].keys():
            as_matrix_3 = asarray([ravel(x['slope'][chan]) for x in loc \
                           for chan in x['slope']])
            as_matrix = hstack((as_matrix, as_matrix_3))
            
        desc = get_descriptives(as_matrix)
        
        with open(filename, 'w', newline='') as f:
            lg.info('Writing to' + str(filename))
            csv_file = writer(f)
            
            if 'count' in glob.keys():
                csv_file.writerow(['Count'] + [glob['count']])
            if 'density' in glob.keys():
                csv_file.writerow(['Density'] + [glob['density']])

            csv_file.writerow(heading_row_1 + heading_row_2 + heading_row_3 \
                              + heading_row_4)            
            csv_file.writerow(['Mean'] + spacer + list(desc['mean']))
            csv_file.writerow(['SD'] + spacer + list(desc['sd']))
            csv_file.writerow(['Mean of ln'] + spacer + list(desc['mean_log']))
            csv_file.writerow(['SD of ln'] + spacer + list(desc['sd_log']))
            idx = 0

            for seg in loc:

                for chan in seg['data'].axis['chan'][0]:
                    idx += 1
                    data_row_1 = [seg[x](chan=chan)[0] for x in sel_params_1]
                    data_row_2 = [seg[x][chan] for x in sel_params_2]
                    
                    if 'dur' in seg.keys():
                        data_row_1 = [seg['dur']] + data_row_1
                    
                    if 'slope' in seg.keys():
                        data_row_3 = [x for y in seg['slope'][chan] for x in y]
                        data_row_2 = data_row_2 + data_row_3
                        
                    if seg['cycle'] is not None:
                        seg['cycle'] = seg['cycle'][2]                    
                        
                    csv_file.writerow([idx,
                                       seg['times'][0],
                                       seg['times'][1],
#                                       seg['n_stitch'],
                                       seg['stage'],
                                       seg['cycle'],
                                       seg['name'],
                                       chan,
                                       ] + data_row_1 + data_row_2)

    def make_title(self, chan, cycle, stage, evt_type):
        """Make a title for plots, etc."""
        cyc_str = None
        if cycle is not None:
            cyc_str = [str(c[2]) for c in cycle]
            cyc_str[0] = 'cycle ' + cyc_str[0]
            
        title = [' + '.join([str(x) for x in y]) for y in [chan, cyc_str, 
                 stage, evt_type] if y is not None]
        
        return ', '.join(title)


def get_descriptives(data):
    """Get mean, SD, and mean and SD of log values.
    
    Parameters
    ----------
    data : ndarray
        Data with segment as first dimension
        and all other dimensions raveled into second dimension.
        
    Returns
    -------
    dict of ndarray
        each entry is a 1-D vector of descriptives over segment dimension        
    """
    output = {}
    dat_log = log(abs(data))
    output['mean'] = mean(data, axis=0)
    output['sd'] = std(data, axis=0)
    output['mean_log'] = mean(dat_log, axis=0)
    output['sd_log'] = std(dat_log, axis=0)
    
    return output

def get_slopes(data, s_freq, level='all', smooth=0.05):
    """Get the slopes (average and/or maximum) for each quadrant of a slow
    wave, as well as the combination of quadrants 2 and 3.
    
    Parameters
    ----------
    data : ndarray
        raw data as vector
    s_freq : int
        sampling frequency
    level : str
        if 'average', returns average slopes (uV / s). if 'maximum', returns 
        the maximum of the slope derivative (uV / s**2). if 'all', returns all.
    smooth : float or None
        if not None, signal will be smoothed by moving average, with a window 
        of this duration
        
    Returns
    -------
    tuple of ndarray
        each array is len 5, with q1, q2, q3, q4 and q23. First array is 
        average slopes and second is maximum slopes.
        
    Notes
    -----
    This function is made to take automatically detected start and end 
    times AS WELL AS manually delimited ones. In the latter case, the first
    and last zero has to be detected within this function.
    """
    idx_trough = data.argmin()
    idx_peak = data.argmax()    
    if idx_trough >= idx_peak:
        return
    
    zero_crossings_0 = where(diff(sign(data[:idx_trough])))[0]
    zero_crossings_1 = where(diff(sign(data[idx_trough:idx_peak])))[0]
    zero_crossings_2 = where(diff(sign(data[idx_peak:])))[0]
    if zero_crossings_1.any():
        idx_zero_1 = zero_crossings_1[0]
    else:
        return
    
    if zero_crossings_0.any():
        idx_zero_0 = zero_crossings_0[-1]
    else:
        idx_zero_0 = 0
        
    if zero_crossings_2.any():
        idx_zero_2 = zero_crossings_2[0]
    else:
        idx_zero_2 = len(data) - 1
        
    avg_slopes = None 
    if level in ['average', 'all']:
        q1 = data[idx_trough] / ((idx_trough - idx_zero_0) / s_freq)
        q2 = data[idx_trough] / ((idx_zero_1 - idx_trough) / s_freq)
        q3 = data[idx_peak] / ((idx_peak - idx_zero_1) / s_freq)
        q4 = data[idx_peak] / ((idx_zero_2 - idx_peak) / s_freq)
        q23 = (data[idx_peak] - data[idx_trough]) \
                / ((idx_peak - idx_trough) / s_freq)
        avg_slopes = asarray([q1, q2, q3, q4, q23])
    
    maxsl = None
    if level in ['maximum', 'all']:
        
        if smooth is not None:
            win = int(smooth * s_freq)
            flat = ones(win)
            data = fftconvolve(data, flat / sum(flat), mode='same')
        
        maxsl = asarray([nan, nan, nan, nan, nan])
        
        if idx_trough - idx_zero_0 >= win:
            maxsl[0] = min(gradient(data[idx_zero_0:idx_trough]))
            
        if idx_zero_1 - idx_trough >= win:
            maxsl[1] = max(gradient(data[idx_trough:idx_zero_1]))
            
        if idx_peak - idx_zero_1 >= win:
            maxsl[2] = max(gradient(data[idx_zero_1:idx_peak]))
            
        if idx_zero_2 - idx_peak >= win:
            maxsl[3] = min(gradient(data[idx_peak:idx_zero_2]))
            
        if idx_peak - idx_trough >= win:
            maxsl[4] = max(gradient(data[idx_trough:idx_peak]))
        
    return avg_slopes, maxsl
        

def _create_data_to_analyze(data, analysis_chans, chan_grp, bundles,
                            concat_chan=False, evt_chan_only=False,
                            parent=None):
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
    bundles : list of dict
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
    parent : QWidget, opt
        For use with GUI, as parent widget for the progress bar

    Returns
    -------
    list of dict
        each item is a dict where 'data' is an instance of ChanTime for a
        single segment of signal, 'name' is the event type, if applicable, and
        with 'chan' (str), 'stage' (str) and 'cycle' (int)
    """
    if parent is not None:
        progress = QProgressDialog('Fetching signal', 'Abort',
                                   0, len(bundles), parent)
        progress.setWindowModality(Qt.ApplicationModal)

    s_freq = data.s_freq
    output = []

    for i, seg in enumerate(bundles):
        if parent is not None:
            progress.setValue(i)

        times = [(int(t0 * s_freq),
                  int(t1 * s_freq)) for (t0, t1) in seg['times']]
        #n_stitch = len(times) - 1

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
        one_segment.data[0] = concatenate(all_epoch_data, axis=1)

        if concat_chan and len(one_segment.axis['chan'][0]) > 1:
            one_segment.data[0] = ravel(one_segment.data[0])
            one_segment.axis['chan'][0] = asarray([(', ').join(
                    all_chan_grp_name)], dtype='U')
            # axis['time'] should not be used in this case


        output.append({'data': one_segment,
                       'chan': these_chans,
                       'stage': seg['stage'],
                       'cycle': seg['cycle'],
                       'name': seg['name'],
#                       'n_stitch': n_stitch
                       })

    if parent is not None:
        progress.setValue(i + 1)

    return output


def _amax(x, axis, keepdims=None):
    return amax(x, axis=axis)

def _amin(x, axis, keepdims=None):
    return amin(x, axis=axis)

def _ptp(x, axis, keepdims=None):
    return ptp(x, axis=axis)

def _mean(x, axis, keepdims=None):
    return mean(x, axis=axis)

class PlotCanvas(FigureCanvas):
    """Widget for showing plots."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        if Figure is None:
            return
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
  
    def plot(self, x, y, title, ylabel, log='log y-axis', idx_lim=(1, -1)):
        """Plot the data.

        Parameters
        ----------
        x : ndarray
            vector with frequencies
        y : ndarray
            vector with amplitudes
        title : str
            title of the plot, to appear above it
        ylabel : str
            label for the y-axis
        log : str
            'log y-axis', 'log both axes' or 'linear', to set axis scaling
        idx_lim : tuple of (int or None)
            indices of the data to plot. by default, the first value is left
            out, because of assymptotic tendencies near 0 Hz.
        """
        x = x[slice(*idx_lim)]
        y = y[slice(*idx_lim)]
        ax = self.figure.add_subplot(111)
        ax.set_title(title)
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel(ylabel)

        if 'log y-axis' == log:
            ax.semilogy(x, y, 'r-')
        elif 'log both axes' == log:
            ax.loglog(x, y, 'r-')
        elif 'linear' == log:
            ax.plot(x, y, 'r-')


class PlotDialog(QDialog):
    """Dialog for displaying plots."""
    def __init__(self, parent=None):
        if Figure is None:
            return
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)

        self.parent = parent
        self.canvas = PlotCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.create_dialog()

    def create_dialog(self):
        """Create the basic dialog."""
        self.bbox = QDialogButtonBox(QDialogButtonBox.Close)
        self.idx_close = self.bbox.button(QDialogButtonBox.Close)
        self.idx_close.pressed.connect(self.reject)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addLayout(btnlayout)
        layout.addStretch(1)
        self.setLayout(layout)
