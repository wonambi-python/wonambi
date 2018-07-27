"""Module to detect spindles.
"""
from logging import getLogger
from numpy import (absolute, arange, argmax, argmin, asarray, concatenate, cos,
                   diff, exp, empty, floor, histogram, hstack, insert, invert,
                   logical_and, mean, median, nan, ones, percentile, pi, ptp, 
                   real, sqrt, square, std, vstack, where, zeros)
from scipy.ndimage.filters import gaussian_filter
from scipy.signal import (argrelmax, butter, cheby2, filtfilt, 
                          fftconvolve, hilbert, periodogram, remez, 
                          sosfiltfilt, tukey)
from scipy.fftpack import next_fast_len
try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QProgressDialog
except ImportError:
    pass

from ..graphoelement import Spindles

lg = getLogger(__name__)
MAX_FREQUENCY_OF_INTEREST = 50
MAX_DURATION = 10


class DetectSpindle:
    """Design spindle detection on a single channel.

    Parameters
    ----------
    method : str
        one of the predefined methods
    frequency : tuple of float
        low and high frequency of spindle band
    duration : tuple of float
        min and max duration of spindles
    """
    def __init__(self, method='Moelle2011', frequency=None, duration=None,
                 merge=True):

        self.method = method
        self.merge = merge
        self.min_interval = 0
        self.det_thresh_hi = 0
        self.power_peaks = 'interval'
        self.frequency = frequency
        self.rolloff = 0

        if method == 'Ferrarelli2007':
            if self.frequency is None:
                self.frequency = (11, 15)
            self.rolloff = 0.9
            self.det_remez = {'freq': self.frequency,
                              'rolloff': self.rolloff,
                              'dur': 1.18
                              }
            self.duration = (0.3, 3)
            self.det_wavelet = {'sd': None}
            self.det_thresh_lo = 8
            self.sel_thresh = 2
            self.moving_rms = {'dur': None}
            self.smooth = {'dur': None}

        elif method == 'Nir2011':
            if self.frequency is None:
                self.frequency = (9.2, 16.8)
            self.det_butter = {'order': 2,
                               'freq': self.frequency,
                               }
            self.duration = (0.5, 2)
            self.det_wavelet = {'sd': None}
            self.det_thresh_lo = 3
            self.sel_thresh = 1
            self.min_interval = 1
            self.moving_rms = {'dur': None}
            self.smooth = {'dur': .04}  # is in fact sigma

        elif method == 'Moelle2011':
            if self.frequency is None:
                self.frequency = (9, 15)
            self.rolloff = 1.7
            self.det_remez = {'freq': self.frequency,
                              'rolloff': self.rolloff,
                              'dur': 1.18
                               }
            self.duration = (0.5, 3)
            self.det_wavelet = {'sd': None}
            self.det_thresh_lo = 1.5
            self.sel_thresh = None
            self.moving_rms = {'dur': .2}
            self.smooth = {'dur': .2}
        
        elif method == 'Wamsley2012':
            if self.frequency is None:
                self.frequency = (12, 15)
            self.det_wavelet = {'f0': mean(self.frequency),
                                'sd': .5,
                                'dur': 2,
                                }
            self.duration = (0.3, 3)
            self.det_thresh_lo = 4.5
            self.sel_thresh = None  # necessary for gui/detect
            self.moving_rms = {'dur': None}
            self.smooth = {'dur': .1}

        elif method == 'Ray2015':
            if self.frequency is None:
                self.frequency = (11, 16)
            self.cdemod = {'freq': mean(self.frequency)}
            self.det_butter = {'freq': (0.3, 35),
                               'order': 4}
            self.det_low_butter = {'freq': 5,
                                   'order': 4}
            self.duration = (.49, None)
            self.det_wavelet = {'sd': None}
            self.det_thresh_lo = 2.33
            self.sel_thresh = 0.1
            self.smooth = {'dur': 2 / self.cdemod['freq']}
            self.min_interval = 0.25 # they only start looking again after .25s
            self.zwin = {'dur': 60}
        
        elif 'FASST' in method:
            if self.frequency is None:
                self.frequency = (11, 18)
            self.det_butter = {'freq': self.frequency,
                               'order': 4}
            self.duration = (.4, 1.3)
            self.det_wavelet = {'sd': None}
            self.det_thresh_lo = 90
            self.sel_thresh = None
            self.moving_rms = {'dur': .1}
            self.smooth = {'dur': .1}
            self.min_interval = 1
        
        elif method == 'UCSD':
            if self.frequency is None:
                self.frequency = (10, 16)
            self.det_wavelet = {'freqs': arange(self.frequency[0],
                                                self.frequency[1] + .5, .5),
                                'dur': 1,
                                'width': .5,
                                'win': .5,
                                'sd': None
                                }
            self.duration = (0.3, 3)
            self.det_thresh_lo = 2  # wavelet_peak_thresh
            self.sel_wavelet = {'freqs': arange(self.frequency[0],
                                                self.frequency[1] + .5, .5),
                                'dur': 1,
                                'width': .2,
                                'win': .2,
                                }
            self.sel_thresh = 1
            self.ratio_thresh = .5
            self.moving_rms = {'dur': None}
            self.smooth = {'dur': None}

        elif method == 'Concordia':
            if self.frequency is None:
                self.frequency = (10, 16)
            self.det_butter = {'order': 2,
                               'freq': self.frequency,
                               }
            self.duration = (0.5, 3)
            self.det_wavelet = {'sd': None}
            self.det_thresh_lo = 3
            self.det_thresh_hi = 10
            self.sel_thresh = 1
            self.moving_rms = {'dur': .2}
            self.smooth = {'dur': .2}
            self.min_interval = 0.2

        else:
            raise ValueError('Unknown method')
            
        if frequency is not None:
            self.frequency = frequency  
            
        if duration is not None:
            self.duration = duration

    def __repr__(self):
        return ('detsp_{0}_{1:02}-{2:02}Hz_{3:04.1f}-{4:04.1f}s'
                ''.format(self.method, self.frequency[0], self.frequency[1],
                          self.duration[0], self.duration[1]))

    def __call__(self, data, parent=None):
        """Detect spindles on the data.

        Parameters
        ----------
        data : instance of Data
            data used for detection
        parent : QWidget
            for use with GUI, as parent widget for the progress bar

        Returns
        -------
        instance of graphoelement.Spindles
            description of the detected spindles
        """
        if parent is not None:
            progress = QProgressDialog('Finding spindles', 'Abort', 
                                       0, data.number_of('chan')[0], parent)
            progress.setWindowModality(Qt.ApplicationModal)
        
        spindle = Spindles()
        spindle.chan_name = data.axis['chan'][0]
        spindle.det_value_lo = zeros(data.number_of('chan')[0])
        spindle.det_value_hi = zeros(data.number_of('chan')[0])
        spindle.sel_value = zeros(data.number_of('chan')[0])
        spindle.density = zeros(data.number_of('chan')[0])
        
        if self.duration[1] is None:
            self.duration = self.duration[0], MAX_DURATION

        all_spindles = []
        i = 0
        for i, chan in enumerate(data.axis['chan'][0]):
                
            lg.info('Detecting spindles on chan %s', chan)
            time = hstack(data.axis['time'])
            dat_orig = hstack(data(chan=chan))

            if self.method == 'Ferrarelli2007':
                sp_in_chan, values, density = detect_Ferrarelli2007(dat_orig,
                                                                    data.s_freq,
                                                                    time,
                                                                    self)

            elif self.method == 'Nir2011':
                sp_in_chan, values, density = detect_Nir2011(dat_orig,
                                                             data.s_freq,
                                                             time, self)
            
            elif self.method == 'Wamsley2012':
                sp_in_chan, values, density = detect_Wamsley2012(dat_orig,
                                                                 data.s_freq,
                                                                 time, self)

            elif self.method == 'UCSD':
                sp_in_chan, values, density = detect_UCSD(dat_orig,
                                                          data.s_freq, time,
                                                          self)
            elif self.method == 'Moelle2011':
                sp_in_chan, values, density = detect_Moelle2011(dat_orig,
                                                                data.s_freq,
                                                                time, self)
                
            elif self.method == 'Ray2015':
                sp_in_chan, values, density = detect_Ray2015(dat_orig,
                                                            data.s_freq,
                                                            time, self)
                
            elif self.method == 'FASST':
                sp_in_chan, values, density = detect_FASST(dat_orig,
                                                           data.s_freq,
                                                           time, self,
                                                           submethod='abs')
                
            elif self.method == 'FASST2':
                sp_in_chan, values, density = detect_FASST(dat_orig,
                                                           data.s_freq,
                                                           time, self,
                                                           submethod='rms')            
            elif self.method == 'Concordia':
                sp_in_chan, values, density = detect_Concordia(dat_orig,
                                                               data.s_freq,
                                                               time, self)
            else:
                raise ValueError('Unknown method')

            spindle.det_value_lo[i] = values['det_value_lo']
            spindle.det_value_hi[i] = values['det_value_hi']
            spindle.sel_value[i] = values['sel_value']
            spindle.density[i] = density

            for sp in sp_in_chan:
                sp.update({'chan': chan})

            all_spindles.extend(sp_in_chan)
            
            if parent is not None:
                progress.setValue(i)
                if progress.wasCanceled():
                    return
            # end of loop over chan

        spindle.events = sorted(all_spindles, key=lambda x: x['start'])
        lg.info(str(len(spindle.events)) + ' spindles detected.')

        if self.merge and len(data.axis['chan'][0]) > 1:
            spindle.events = merge_close(spindle.events, self.min_interval)

        if parent is not None:
            progress.setValue(i + 1)            
        
        return spindle


def detect_Ray2015(dat_orig, s_freq, time, opts):
    """Spindle detection based on Ray et al., 2015
    
    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSpindle'
        'det_wavelet' : dict
            parameters for 'morlet',
        'smooth' : dict
            parameters for 'moving_avg'
        'det_thresh' : float
            detection threshold
        'sel_thresh' : nan
            not used, but keep it for consistency with the other methods
        'duration' : tuple of float
            min and max duration of spindles

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo' with detection value, 'det_value_hi' is nan,
        'sel_value' is nan (for consistency with other methods)
    float
        spindle density, per 30-s epoch

    References
    ----------
    Ray, L. B. et al. Front. Hum. Neurosci. 9-16 (2015).
    """
    dat_det = transform_signal(dat_orig, s_freq, 'butter', opts.det_butter)
    dat_det = transform_signal(dat_det, s_freq, 'cdemod', opts.cdemod)
    dat_det = transform_signal(dat_det, s_freq, 'low_butter', 
                               opts.det_low_butter)
    dat_det = transform_signal(dat_det, s_freq, 'tri_smooth', opts.smooth)
    dat_det = transform_signal(dat_det, s_freq, 'abs2')
    dat_det = transform_signal(dat_det, s_freq, 'zscore', opts.zwin)
    
    det_value = opts.det_thresh_lo
    sel_value = opts.sel_thresh
    
    events = detect_events(dat_det, 'above_thresh', det_value)
    
    if events is not None:
        events = select_events(dat_det, events, 'above_thresh', sel_value)
        
        events = _merge_close(dat_det, events, time, opts.min_interval)
        events = within_duration(events, time, opts.duration)
        events = remove_straddlers(events, time, s_freq)

        power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
        powers = band_power(events, dat_orig, s_freq, opts.frequency)
        sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                                   dat_orig, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value_lo': det_value, 'det_value_hi': nan, 'sel_value': nan}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density

def detect_Wamsley2012(dat_orig, s_freq, time, opts):
    """Spindle detection based on Wamsley et al. 2012

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSpindle'
        'det_wavelet' : dict
            parameters for 'morlet',
        'smooth' : dict
            parameters for 'moving_avg'
        'det_thresh' : float
            detection threshold
        'sel_thresh' : nan
            not used, but keep it for consistency with the other methods
        'duration' : tuple of float
            min and max duration of spindles

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo' with detection value, 'det_value_hi' is nan,
        'sel_value' is nan (for consistency with other methods)
    float
        spindle density, per 30-s epoch

    References
    ----------
    Wamsley, E. J. et al. Biol. Psychiatry 71, 154-61 (2012).
    """
    dat_det = transform_signal(dat_orig, s_freq, 'morlet', opts.det_wavelet)
    dat_det = real(dat_det ** 2) ** 2
    dat_det = transform_signal(dat_det, s_freq, 'moving_avg', opts.smooth)

    det_value = define_threshold(dat_det, s_freq, 'mean', opts.det_thresh_lo)

    events = detect_events(dat_det, 'above_thresh', det_value)

    if events is not None:
        events = _merge_close(dat_det, events, time, opts.min_interval)
        events = within_duration(events, time, opts.duration)
        events = remove_straddlers(events, time, s_freq)

        power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
        powers = band_power(events, dat_orig, s_freq, opts.frequency)
        sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                                   dat_orig, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value_lo': det_value, 'det_value_hi': nan, 'sel_value': nan}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density


def detect_Nir2011(dat_orig, s_freq, time, opts):
    """Spindle detection based on Nir et al. 2011

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSpindle'
        'det_butter' : dict
            parameters for 'butter',
        'smooth' : dict
            parameters for 'gaussian'
        'det_thresh' : float
            detection threshold
        'sel_thresh' : float
            selection threshold
        'min_interval' : float
            minimum interval between consecutive events
        'duration' : tuple of float
            min and max duration of spindles

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo' with detection value, 'det_value_hi' with nan,
        'sel_value' with selection value
    float
        spindle density, per 30-s epoch

    Notes
    -----
    This paper also selects channels carefully:
    'First, the channels with spindle activity in NREM sleep were
    chosen for further analysis.'

    'Third, those channels, in which an increase in spectral power
    within the detected events was restricted to the spindle-frequency
    range (10-16 Hz) rather than broadband.'

    References
    ----------
    Nir, Y. et al. Neuron 70, 153-69 (2011).
    """
    dat_det = transform_signal(dat_orig, s_freq, 'butter', opts.det_butter)
    dat_det = transform_signal(dat_det, s_freq, 'hilbert')
    dat_det = transform_signal(dat_det, s_freq, 'abs')
    dat_det = transform_signal(dat_det, s_freq, 'gaussian', opts.smooth)

    det_value = define_threshold(dat_det, s_freq, 'mean+std',
                                 opts.det_thresh_lo)
    sel_value = define_threshold(dat_det, s_freq, 'mean+std', opts.sel_thresh)

    events = detect_events(dat_det, 'above_thresh', det_value)

    if events is not None:
        events = _merge_close(dat_det, events, time, opts.min_interval)

        events = select_events(dat_det, events, 'above_thresh', sel_value)

        events = within_duration(events, time, opts.duration)
        events = remove_straddlers(events, time, s_freq)

        power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
        powers = band_power(events, dat_orig, s_freq, opts.frequency)
        sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                                   dat_orig, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value_lo': det_value, 'det_value_hi': nan,
              'sel_value': sel_value}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density


def detect_Ferrarelli2007(dat_orig, s_freq, time, opts):
    """Spindle detection based on Ferrarelli et al. 2007, and scripts obtained
    from Warby et al. (2014).

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSpindle'
        'det_cheby2' : dict
            parameters for 'cheby2',
        'det_thresh' : float
            detection threshold
        'sel_thresh' : float
            selection threshold
        'duration' : tuple of float
            min and max duration of spindles

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo' with detection value, 'det_value_hi' with nan,
        'sel_value' with selection value
    float
        spindle density, per 30-s epoch

    References
    ----------
    Ferrarelli, F. et al. Am. J. Psychiatry 164, 483-92 (2007).
    Warby, S. C. et al. Nat. Meth. 11(4), 385-92 (2014).
    """
    dat_det = transform_signal(dat_orig, s_freq, 'remez', opts.det_remez)
    dat_det = transform_signal(dat_det, s_freq, 'abs')
    
    idx_env = peaks_in_time(dat_det)
    idx_peak = idx_env[peaks_in_time(dat_det[idx_env])]

    det_value = define_threshold(dat_det, s_freq, 'mean', opts.det_thresh_lo)
    sel_value = define_threshold(dat_det[idx_peak], s_freq, 'histmax', 
                                 opts.sel_thresh, nbins=120)
    
    events_env = detect_events(dat_det[idx_env], 'above_thresh', det_value)
    
    if events_env is not None:
        
        events_env = select_events(dat_det[idx_env], events_env, 
                                   'above_thresh', sel_value)  
        events = idx_env[events_env]

        # merging is necessary, because detected spindles may overlap if the
        # signal envelope does not dip below sel_thresh between two peaks above 
        # det_thresh
        events = _merge_close(dat_det, events, time, opts.min_interval)
        events = within_duration(events, time, opts.duration)        
        events = remove_straddlers(events, time, s_freq)

        power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
        powers = band_power(events, dat_orig, s_freq, opts.frequency)
        sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                                   dat_orig, time, s_freq)
        lg.info('Spindles in chan: ' + str(len(sp_in_chan)))

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value_lo': det_value, 'det_value_hi': nan,
              'sel_value': sel_value}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density


def detect_Moelle2011(dat_orig, s_freq, time, opts):
    """Spindle detection based on Moelle et al. 2011

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSpindle'
        'det_remez' : dict
            parameters for 'remez',
        'moving_rms' : dict
            parameters for 'moving_rms'
        'smooth' : dict
            parameters for 'moving_avg'
        'det_thresh' : float
            detection threshold
        'sel_thresh' : nan
            not used, but keep it for consistency with the other methods
        'duration' : tuple of float
            min and max duration of spindles

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo' with detection value, 'det_value_hi' with nan,
        'sel_value' with nan
    float
        spindle density, per 30-s epoch

    References
    ----------
    Moelle, M. et al. J. Neurosci. 22(24), 10941-7 (2002).
    """
    dat_det = transform_signal(dat_orig, s_freq, 'remez', opts.det_remez)
    dat_det = transform_signal(dat_det, s_freq, 'moving_rms', opts.moving_rms)
    dat_det = transform_signal(dat_det, s_freq, 'moving_avg', opts.smooth)

    det_value = define_threshold(dat_det, s_freq, 'mean+std',
                                 opts.det_thresh_lo)

    events = detect_events(dat_det, 'above_thresh', det_value)

    if events is not None:
        events = _merge_close(dat_det, events, time, opts.min_interval)
        events = within_duration(events, time, opts.duration)
        events = remove_straddlers(events, time, s_freq)

        power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
        powers = band_power(events, dat_orig, s_freq, opts.frequency)
        sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                                   dat_orig, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value_lo': det_value, 'det_value_hi': nan, 'sel_value': nan}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density


def detect_FASST(dat_orig, s_freq, time, opts, submethod='rms'):
    """Spindle detection based on FASST method, itself based on Moelle et al. 
    (2002).
    
    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSpindle'
        'det_remez' : dict
            parameters for 'remez',
        'moving_rms' : dict
            parameters for 'moving_rms'
        'smooth' : dict
            parameters for 'moving_avg'
        'det_thresh' : float
            detection threshold
        'sel_thresh' : nan
            not used, but keep it for consistency with the other methods
        'duration' : tuple of float
            min and max duration of spindles
    submethod : str
        'abs' (rectified) or 'rms' (root-mean-square)

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo' with detection value, 'det_value_hi' with nan,
        'sel_value' with nan
    float
        spindle density, per 30-s epoch

    References
    ----------
    Leclercq, Y. et al. Compu. Intel. and Neurosci. (2011).
    """
    dat_det = transform_signal(dat_orig, s_freq, 'butter', opts.det_butter)
    
    det_value = percentile(dat_det, opts.det_thresh_lo)
    
    if submethod == 'abs':
        dat_det = transform_signal(dat_det, s_freq, 'abs')
    elif submethod == 'rms':
        dat_det = transform_signal(dat_det, s_freq, 'moving_rms', 
                                   opts.moving_rms)
        
    dat_det = transform_signal(dat_det, s_freq, 'moving_avg', opts.smooth)
    
    events = detect_events(dat_det, 'above_thresh', det_value)

    if events is not None:
        events = within_duration(events, time, opts.duration)
        events = _merge_close(dat_det, events, time, opts.min_interval)
        events = remove_straddlers(events, time, s_freq)

        power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
        powers = band_power(events, dat_orig, s_freq, opts.frequency)
        sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                                   dat_orig, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value_lo': det_value, 'det_value_hi': nan, 'sel_value': nan}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density
    

def detect_UCSD(dat_orig, s_freq, time, opts):
    """Spindle detection based on the UCSD method

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSpindle'
        det_wavelet : dict
            parameters for 'wavelet_real',
        det_thres' : float
            detection threshold
        sel_thresh : float
            selection threshold
        duration : tuple of float
            min and max duration of spindles
        frequency : tuple of float
            low and high frequency of spindle band (for power ratio)
        ratio_thresh : float
            ratio between power inside and outside spindle band to accept them

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo' with detection value, 'det_value_hi' with nan,
        'sel_value' with selection value
    float
        spindle density, per 30-s epoch

    """
    dat_det = transform_signal(dat_orig, s_freq, 'wavelet_real',
                               opts.det_wavelet)

    det_value = define_threshold(dat_det, s_freq, 'median+std',
                                 opts.det_thresh_lo)

    events = detect_events(dat_det, 'maxima', det_value)

    dat_sel = transform_signal(dat_orig, s_freq, 'wavelet_real',
                               opts.sel_wavelet)
    sel_value = define_threshold(dat_sel, s_freq, 'median+std',
                                 opts.sel_thresh)
    events = select_events(dat_sel, events, 'above_thresh', sel_value)

    events = _merge_close(dat_det, events, time, opts.min_interval)
    events = within_duration(events, time, opts.duration)
    events = remove_straddlers(events, time, s_freq)

    events = power_ratio(events, dat_orig, s_freq, opts.frequency,
                         opts.ratio_thresh)

    power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
    powers = band_power(events, dat_orig, s_freq, opts.frequency)
    sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                               dat_orig, time, s_freq)

    values = {'det_value_lo': det_value, 'det_value_hi': nan,
              'sel_value': sel_value}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density


def detect_Concordia(dat_orig, s_freq, time, opts):
    """Spindle detection, experimental Concordia method. Similar to Moelle 2011
    and Nir2011.

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    opts : instance of 'DetectSpindle'
        'det_butter' : dict
            parameters for 'butter',
        'moving_rms' : dict
            parameters for 'moving_rms'
        'smooth' : dict
            parameters for 'moving_avg'
        'det_thresh_lo' : float
            low detection threshold
        'det_thresh_hi' : float
            high detection threshold
        'sel_thresh' : float
            selection threshold
        'duration' : tuple of float
            min and max duration of spindles

    Returns
    -------
    list of dict
        list of detected spindles
    dict
        'det_value_lo', 'det_value_hi' with detection values, 'sel_value' with
        selection value
    float
        spindle density, per 30-s epoch
    """
    dat_det = transform_signal(dat_orig, s_freq, 'butter', opts.det_butter)
    dat_det = transform_signal(dat_det, s_freq, 'moving_rms', opts.moving_rms)
    dat_det = transform_signal(dat_det, s_freq, 'moving_avg', opts.smooth)

    det_value_lo = define_threshold(dat_det, s_freq, 'mean+std',
                                    opts.det_thresh_lo)
    det_value_hi = define_threshold(dat_det, s_freq, 'mean+std',
                                    opts.det_thresh_hi)
    sel_value = define_threshold(dat_det, s_freq, 'mean+std', opts.sel_thresh)

    events = detect_events(dat_det, 'between_thresh',
                           value=(det_value_lo, det_value_hi))

    if events is not None:
        events = _merge_close(dat_det, events, time, opts.min_interval)

        events = select_events(dat_det, events, 'above_thresh', sel_value)

        events = within_duration(events, time, opts.duration)
        events = remove_straddlers(events, time, s_freq)

        power_peaks = peak_in_power(events, dat_orig, s_freq, opts.power_peaks)
        powers = band_power(events, dat_orig, s_freq, opts.frequency)
        sp_in_chan = make_spindles(events, power_peaks, powers, dat_det,
                                   dat_orig, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value_lo': det_value_lo, 'det_value_hi': det_value_hi,
              'sel_value': sel_value}

    density = len(sp_in_chan) * s_freq * 30 / len(dat_orig)

    return sp_in_chan, values, density


def transform_signal(dat, s_freq, method, method_opt=None):
    """Transform the data using different methods.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with all the data for one channel
    s_freq : float
        sampling frequency
    method : str
        one of 'butter', 'cheby2', 'double_butter', 'morlet', 'morlet_real', 
        'hilbert', 'abs', 'moving_avg', 'gaussian', 'remez', 'wavelet_real',
        'low_butter'
    method_opt : dict
        depends on methods

    Returns
    -------
    ndarray (dtype='float')
        vector with all the data for one channel

    Notes
    -----
    double_butter implements an effective bandpass by applying a highpass, 
    followed by a lowpass. This method reduces filter instability, due to 
    underlying numerical instability arising from nyquist / freq, at low freq.
    Wavelets pass only absolute values already, it does not make sense to store
    the complex values.

    Methods
    -------    
    butter has parameters:
        freq : tuple of float
            low and high values for bandpass
        order : int
            filter order (will be effecively doubled by filtfilt)

    cdemod has parameters:
        freq : float
            carrier frequency for complex demodulation
    
    cheby2 has parameters:
        freq : tuple of float
            low and high values for bandpass
        order : int
            filter order (will be effecively doubled by filtfilt)
            
    double_butter has parameters:
        freq : tuple of float
            low and high values for highpass, then lowpass
        order : int
            filter order (will be effecively doubled by filtfilt)

    gaussian has parameters:
        dur : float
            standard deviation of the Gaussian kernel, aka sigma (sec)
            
    low_butter has parameters:
        freq : float
            Highcut frequency, in Hz
        order : int
            filter order (will be effecively doubled by filtfilt)
            
    morlet has parameters:
        f0 : float
            center frequency in Hz
        sd : float
            standard deviation of frequency
        dur : float
            window length in number of standard deviations

    morlet_real has parameters:
        freqs : ndarray
            vector of wavelet frequencies for spindle detection
        dur : float
            duration of the wavelet (sec)
        width : float
            wavelet width
        win : float
            moving average window length (sec) of wavelet convolution

    moving_avg has parameters:
        dur : float
            duration of the window (sec)

    moving_rms has parameters:
        dur : float
            duration of the window (sec)
            
    remez has parameters:
        freq : tuple of float
            low and high values for bandpass
        rolloff : float
            bandwidth, in hertz, between stop and pass frequencies
        dur : float
            dur * s_freq = N, where N is the filter order, a.k.a number of taps
                
    tri_smooth has parameters:
        dur : float
            length of convolution window, base of isosceles triangle
    
    zscore has parameters:
        dur : float
            duration of the z-score sliding window (sec)
    """
    if 'abs' == method:
        dat = absolute(dat)
        
    if 'abs2' == method:
        dat = dat.real**2 + dat.imag**2

    if 'butter' == method:
        freq = method_opt['freq']
        N = method_opt['order']

        nyquist = s_freq / 2
        Wn = asarray(freq) / nyquist
        b, a = butter(N, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)
        
    if 'sosbutter' == method:
        freq = method_opt['freq']
        N = method_opt['order']

        nyquist = s_freq / 2
        Wn = asarray(freq) / nyquist
        sos = butter(N, Wn, btype='bandpass', output='sos')
        dat = sosfiltfilt(sos, dat)
        
    if 'cdemod' == method:
        carr_freq = method_opt['freq']
        carr_sig = exp(-1j * 2 * pi * carr_freq * arange(0, len(dat)) / s_freq)
        
        dat = dat * carr_sig        
    
    if 'cheby2' == method:
        freq = method_opt['freq']
        N = method_opt['order']

        Rs = 40
        nyquist = s_freq / 2
        Wn = asarray(freq) / nyquist
        b, a = cheby2(N, Rs, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)

    if 'double_butter' == method:
        freq = method_opt['freq']
        N = method_opt['order']
        nyquist = s_freq / 2
        
        # Highpass
        Wn = freq[0] / nyquist
        b, a = butter(N, Wn, btype='highpass')
        dat = filtfilt(b, a, dat)
        
        # Lowpass
        Wn = freq[1] / nyquist
        b, a = butter(N, Wn, btype='lowpass')
        dat = filtfilt(b, a, dat)

    if 'gaussian' == method:
        sigma = method_opt['dur']

        dat = gaussian_filter(dat, sigma)        

    if 'hilbert' == method:
        N = len(dat)
        dat = hilbert(dat, N=next_fast_len(N)) # much faster this way
        dat = dat[:N] # truncate away zero-padding
        
    if 'low_butter' == method:
        freq = method_opt['freq']
        N = method_opt['order']
        nyquist = s_freq / 2
        
        Wn = freq / nyquist
        b, a = butter(N, Wn, btype='lowpass')
        dat = filtfilt(b, a, dat)
    
    if 'morlet' == method:
        f0 = method_opt['f0']
        sd = method_opt['sd']
        dur = method_opt['dur']

        wm = _wmorlet(f0, sd, s_freq, dur)
        dat = absolute(fftconvolve(dat, wm, mode='same'))

    if 'moving_avg' == method:
        dur = method_opt['dur']

        flat = ones(int(dur * s_freq))
        dat = fftconvolve(dat, flat / sum(flat), mode='same')

    if 'moving_rms' == method:
        dur = method_opt['dur']
        halfdur = int(floor(s_freq * dur / 2))
        lendat = len(dat)
        rms = zeros((lendat))

        for i in range(lendat):
            rms[i] = sqrt(mean(square(
                    dat[max(0, i - halfdur):min(lendat, i + halfdur)])))
        dat = rms
    
    if 'remez' == method:
        Fp1, Fp2 = method_opt['freq']
        rolloff = method_opt['rolloff']
        dur = method_opt['dur']
        
        N = int(s_freq * dur)
        nyquist = s_freq / 2
        Fs1, Fs2 = Fp1 - rolloff, Fp2 + rolloff
        dens = 20
        
        bpass = remez(N, [0, Fs1, Fp1, Fp2, Fs2, nyquist], [0, 1, 0], 
                      grid_density=dens, fs=s_freq)
        dat = filtfilt(bpass, 1, dat)

    if 'wavelet_real' == method:
        freqs = method_opt['freqs']
        dur = method_opt['dur']
        width = method_opt['width']
        win = int(method_opt['win'] * s_freq)

        wm = _realwavelets(s_freq, freqs, dur, width)
        tfr = empty((dat.shape[0], wm.shape[0]))
        for i, one_wm in enumerate(wm):
            x = abs(fftconvolve(dat, one_wm, mode='same'))
            tfr[:, i] = fftconvolve(x, tukey(win), mode='same')
        dat = mean(tfr, axis=1)
        
    if 'tri_smooth' == method:
        T = int(method_opt['dur'] * s_freq / 2)
        a = arange(T, 0, -1)
        
        H = hstack([a[-1:0:-1], a])
        H = H / sum(H)
        
        dat = fftconvolve(dat, H, mode='same')
    
    if 'zscore' == method:
        dur = int(floor(method_opt['dur'] * s_freq))
        halfdur = int(floor(dur / 2))
        lendat = len(dat)
        stop = lendat - dur
        zs = zeros((lendat))
        
        for i in range(lendat):
            start = min(max(0, i - halfdur), stop)
            end = min(start + dur, lendat)
            windat = dat[start:end]
            zs[i] = (dat[i] - mean(windat)) / std(windat)
        dat = zs

    return dat


def define_threshold(dat, s_freq, method, value, nbins=120):
    """Return the value of the threshold based on relative values.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data after selection-transformation
    s_freq : float
        sampling frequency
    method : str
        one of 'mean', 'median', 'std', 'mean+std', 'median+std', 'histmax'
    value : float
        value to multiply the values for
    nbins : int
        for histmax method, number of bins in the histogram

    Returns
    -------
    float
        threshold in useful units.

    """
    if method == 'mean':
        value = value * mean(dat)
    elif method == 'median':
        value = value * median(dat)
    elif method == 'std':
        value = value * std(dat)
    elif method == 'mean+std':
        value = mean(dat) + value * std(dat)
    elif method == 'median+std':
        value = median(dat) + value * std(dat)
    elif method == 'histmax':
        hist = histogram(dat, bins=nbins)
        idx_maxbin = argmax(hist[0])
        maxamp = mean((hist[1][idx_maxbin], hist[1][idx_maxbin + 1]))
        value = value * maxamp

    return value


def peaks_in_time(dat, troughs=False):
    """Find indices of peaks or troughs in data.
    
    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data
    troughs : bool
        if True, will return indices of troughs instead of peaks
        
    Returns
    -------
    nadarray of int
        indices of peaks (or troughs) in dat
        
    Note
    ----
    This function does not deal well with flat signal; when the signal is not 
    increasing, it is assumed to be descreasing. As a result, this function
    finds troughs where the signal begins to increase after either decreasing 
    or remaining constant
    """
    diff_dat = diff(dat)
    increasing = zeros(len(diff_dat))
    increasing[diff_dat > 0] = 1 # mask for all points where dat is increasing
    flipping = diff(increasing) # peaks are -1, troughs are 1, the rest is zero
    
    target = -1 if not troughs else 1
        
    return where(flipping == target)[0]


def detect_events(dat, method, value=None):
    """Detect events using 'above_thresh', 'below_thresh' or
    'maxima' method.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data after transformation
    method : str
        'above_thresh', 'below_thresh' or 'maxima'
    value : float or tuple of float
        for 'above_thresh' or 'below_thresh', it's the value of threshold for
        the event detection
        for 'between_thresh', it's the lower and upper threshold as tuple
        for 'maxima', it's the distance in s from the peak to find a minimum

    Returns
    -------
    ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples

    """
    if 'thresh' in method:

        if method == 'above_thresh':
            above_det = dat >= value
            detected = _detect_start_end(above_det)

        if method == 'below_thresh':
            below_det = dat < value
            detected = _detect_start_end(below_det)

        if method == 'between_thresh':
            above_det = dat >= value[0]
            below_det = dat < value[1]
            between_det = logical_and(above_det, below_det)
            detected = _detect_start_end(between_det)

        if detected is None:
            return None
        
        if method == 'above_thresh':    
            # add the location of the peak in the middle
            detected = insert(detected, 1, 0, axis=1)
            for i in detected:
                i[1] = i[0] + argmax(dat[i[0]:i[2]])

        if method in ['below_thresh', 'between_thresh']:
            # add the location of the trough in the middle
            detected = insert(detected, 1, 0, axis=1)
            for i in detected:
                i[1] = i[0] + argmin(dat[i[0]:i[2]])

    if method == 'maxima':
        peaks = argrelmax(dat)[0]
        detected = vstack((peaks, peaks, peaks)).T

        if value is not None:
            detected = detected[dat[peaks] > value, :]

    return detected


def select_events(dat, detected, method, value):
    """Select start sample and end sample of the events.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data after selection-transformation
    detected : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    method : str
        'above_thresh', 'below_thresh'
    value : float
        for 'threshold', it's the value of threshold for the spindle selection.

    Returns
    -------
    ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples

    """
    if method == 'above_thresh':
        above_sel = dat >= value
        detected = _select_period(detected, above_sel)
    elif method == 'below_thresh':
        below_sel = dat <= value
        detected = _select_period(detected, below_sel)

    return detected


def merge_close(events, min_interval, merge_to_longer=False):
    """Merge events that are separated by a less than a minimum interval.

    Parameters
    ----------
    events : list of dict
        events with 'start' and 'end' times, from one or several channels.
        **Events must be sorted by their start time.**
    min_interval : float
        minimum delay between consecutive events, in seconds
    merge_to_longer : bool (default: False)
        If True, info (chan, peak, etc.) from the longer of the 2 events is
        kept. Otherwise, info from the earlier onset spindle is kept.

    Returns
    -------
    list of dict
        original events list with close events merged.
    """
    half_iv = min_interval / 2
    merged = []

    for higher in events:

        if not merged:
            merged.append(higher)

        else:
            lower = merged[-1]

            if higher['start'] - half_iv <= lower['end'] + half_iv:

                if merge_to_longer and (higher['end'] - higher['start'] >
                lower['end'] - lower['start']):
                    start = min(lower['start'], higher['start'])
                    higher.update({'start': start})
                    merged[-1] = higher

                else:
                    end = max(lower['end'], higher['end'])
                    merged[-1].update({'end': end})

            else:
                merged.append(higher)

    return merged


def within_duration(events, time, limits):
    """Check whether event is within time limits.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    time : ndarray (dtype='float')
        vector with time points
    limits : tuple of float
        low and high limit for spindle duration

    Returns
    -------
    ndarray (dtype='int')
        N x 3 matrix with start , peak, end samples
    """
    min_dur = max_dur = ones(events.shape[0], dtype=bool)
    
    if limits[0] is not None:
        min_dur = time[events[:, 2] - 1] - time[events[:, 0]] >= limits[0]
    
    if limits[1] is not None:
        max_dur = time[events[:, 2] - 1] - time[events[:, 0]] <= limits[1]

    return events[min_dur & max_dur, :]


def remove_straddlers(events, time, s_freq, toler=0.1):
    """Reject an event if it straddles a stitch, by comparing its 
    duration to its timespan.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x M matrix with start, ..., end samples
    time : ndarray (dtype='float')
        vector with time points
    s_freq : float
        sampling frequency
    toler : float, def=0.1
        maximum tolerated difference between event duration and timespan

    Returns
    -------
    ndarray (dtype='int')
        N x M matrix with start , ..., end samples
    """
    dur = (events[:, -1] - 1 - events[:, 0]) / s_freq
    continuous = time[events[:, -1] - 1] - time[events[:, 0]] - dur < toler
    
    return events[continuous, :]
    


def power_ratio(events, dat, s_freq, limits, ratio_thresh):
    """Estimate the ratio in power between spindle band and lower frequencies.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    dat : ndarray (dtype='float')
        vector with the original data
    s_freq : float
        sampling frequency
    limits : tuple of float
        high and low frequencies for spindle band
    ratio_thresh : float
        ratio between spindle vs non-spindle amplitude

    Returns
    -------
    ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples

    Notes
    -----
    In the original matlab script, it uses amplitude, not power.

    """
    ratio = empty(events.shape[0])
    for i, one_event in enumerate(events):

        x0 = one_event[0]
        x1 = one_event[2]

        if x0 < 0 or x1 >= len(dat):
            ratio[i] = 0

        else:
            f, Pxx = periodogram(dat[x0:x1], s_freq, scaling='spectrum')
            Pxx = sqrt(Pxx)  # use amplitude

            freq_sp = (f >= limits[0]) & (f <= limits[1])
            freq_nonsp = (f <= limits[1])

            ratio[i] = mean(Pxx[freq_sp]) / mean(Pxx[freq_nonsp])

    events = events[ratio > ratio_thresh, :]

    return events


def peak_in_power(events, dat, s_freq, method, value=None):
    """Define peak in power of the signal.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    dat : ndarray (dtype='float')
        vector with the original data
    s_freq : float
        sampling frequency
    method : str or None
        'peak' or 'interval'. If None, values will be all NaN
    value : float
        size of the window around peak, or nothing (for 'interval')

    Returns
    -------
    ndarray (dtype='float')
        vector with peak frequency

    """
    dat = diff(dat)  # remove 1/f

    peak = empty(events.shape[0])
    peak.fill(nan)

    if method is not None:
        for i, one_event in enumerate(events):

            if method == 'peak':
                x0 = one_event[1] - value / 2 * s_freq
                x1 = one_event[1] + value / 2 * s_freq

            elif method == 'interval':
                x0 = one_event[0]
                x1 = one_event[2]

            if x0 < 0 or x1 >= len(dat):
                peak[i] = nan
            else:
                f, Pxx = periodogram(dat[x0:x1], s_freq)
                idx_peak = Pxx[f < MAX_FREQUENCY_OF_INTEREST].argmax()
                peak[i] = f[idx_peak]

    return peak


def band_power(events, dat, s_freq, frequency):
    """Define power of the signal within frequency band.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    dat : ndarray (dtype='float')
        vector with the original data
    s_freq : float
        sampling frequency
    frequency : tuple of float
        low and high frequency of spindle band, for window

    Returns
    -------
    ndarray (dtype='float')
        vector with power
    """
    dat = diff(dat)  # remove 1/f

    pw = empty(events.shape[0])
    pw.fill(nan)

    for i, one_event in enumerate(events):

        x0 = one_event[0]
        x1 = one_event[2]

        if x0 < 0 or x1 >= len(dat):
            pw[i] = nan
        else:
            sf, Pxx = periodogram(dat[x0:x1], s_freq)
            # find nearest frequencies in sf
            b0 = asarray([abs(x - frequency[0]) for x in sf]).argmin()
            b1 = asarray([abs(x - frequency[1]) for x in sf]).argmin()
            pw[i] = mean(Pxx[b0:b1])

    return pw


def make_spindles(events, power_peaks, powers, dat_det, dat_orig, time,
                  s_freq):
    """Create dict for each spindle, based on events of time points.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples, and peak frequency
    power_peaks : ndarray (dtype='float')
        peak in power spectrum for each event
    powers : ndarray (dtype='float')
        average power in power spectrum for each event
    dat_det : ndarray (dtype='float')
        vector with the data after detection-transformation (to compute peak)
    dat_orig : ndarray (dtype='float')
        vector with the raw data on which detection was performed
    time : ndarray (dtype='float')
        vector with time points
    s_freq : float
        sampling frequency

    Returns
    -------
    list of dict
        list of all the spindles, with information about start_time, peak_time,
        end_time (s), peak_val (signal units), area_under_curve
        (signal units * s), peak_freq (Hz)
    """
    i, events = _remove_duplicate(events, dat_det)
    power_peaks = power_peaks[i]

    spindles = []
    for i, one_peak, one_pwr in zip(events, power_peaks, powers):
        one_spindle = {'start': time[i[0]],
                       'end': time[i[2] - 1],
                       'peak_time': time[i[1]],
                       'peak_val_det': dat_det[i[1]],
                       'peak_val_orig': dat_orig[i[1]],
                       'dur': (i[2] - i[0]) / s_freq,
                       'auc_det': sum(dat_det[i[0]:i[2]]) / s_freq,
                       'auc_orig': sum(dat_orig[i[0]:i[2]]) / s_freq,
                       'rms_det': sqrt(mean(square(dat_det[i[0]:i[2]]))),
                       'rms_orig': sqrt(mean(square(dat_orig[i[0]:i[2]]))),
                       'power_orig': one_pwr,
                       'peak_freq': one_peak,
                       'ptp_det': ptp(dat_det[i[0]:i[2]]),
                       'ptp_orig': ptp(dat_orig[i[0]:i[2]])
                       }
        spindles.append(one_spindle)

    return spindles


def _remove_duplicate(old_events, dat):
    """Remove duplicates from the events.

    Parameters
    ----------
    old_events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    dat : ndarray (dtype='float')
        vector with the data after detection-transformation (to compute peak)

    Returns
    -------
    ndarray (dtype='int')
        vector of indices of the events to keep
    ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples

    Notes
    -----
    old_events is assumed to be sorted. It only checks for the start time and
    end time. When two (or more) events have the same start time and the same
    end time, then it takes the largest peak.

    There is no tolerance, indices need to be identical.
    """
    diff_events = diff(old_events, axis=0)
    dupl = where((diff_events[:, 0] == 0) & (diff_events[:, 2] == 0))[0]
    dupl += 1  # more convenient, it copies old_event first and then compares

    n_nondupl_events = old_events.shape[0] - len(dupl)
    new_events = zeros((n_nondupl_events, old_events.shape[1]), dtype='int')
    if len(dupl):
        lg.debug('Removing ' + str(len(dupl)) + ' duplicate events')

    i = 0
    indices = []
    for i_old, one_old_event in enumerate(old_events):
        if i_old not in dupl:
            new_events[i, :] = one_old_event
            i += 1
            indices.append(i_old)
        else:
            peak_0 = new_events[i - 1, 1]
            peak_1 = one_old_event[1]
            if dat[peak_0] >= dat[peak_1]:
                new_events[i - 1, 1] = peak_0
            else:
                new_events[i - 1, 1] = peak_1

    return indices, new_events


def _detect_start_end(true_values):
    """From ndarray of bool values, return intervals of True values.

    Parameters
    ----------
    true_values : ndarray (dtype='bool')
        array with bool values

    Returns
    -------
    ndarray (dtype='int')
        N x 2 matrix with starting and ending times.
    """
    neg = zeros((1), dtype='bool')
    int_values = asarray(concatenate((neg, true_values[:-1], neg)), 
                         dtype='int')
    # must discard last value to avoid axis out of bounds
    cross_threshold = diff(int_values)

    event_starts = where(cross_threshold == 1)[0]
    event_ends = where(cross_threshold == -1)[0]

    if len(event_starts):
        events = vstack((event_starts, event_ends)).T

    else:
        events = None

    return events


def _select_period(detected, true_values):
    """For the detected values, we check when it goes above/below the
    selection.

    Parameters
    ----------
    detected : ndarray (dtype='int')
        N x 3 matrix with starting and ending times.
    true_values : ndarray (dtype='bool')
        array with bool values

    Returns
    -------
    ndarray (dtype='int')
        N x 2 matrix with starting and ending times, but these periods are
        usually larger than those of the input, because the selection window is
        usually more lenient (lower threshold) than the detection window.

    Notes
    -----
    Both start and end time points are inclusive (not python convention, but
    matlab convention) because these values are converted to time points later.
    """
    true_values = invert(true_values)

    for one_spindle in detected:
        # get the first time point when it goes above/below selection thres
        start_sel = where(true_values[:one_spindle[0]])[0]
        if start_sel.any():
            one_spindle[0] = start_sel[-1]

        # get the last time point when it stays above/below selection thres
        end_sel = where(true_values[one_spindle[2]:])[0] - 1
        if end_sel.any():
            one_spindle[2] += end_sel[0]

    return detected


def _merge_close(dat, events, time, min_interval):
    """Merge together events separated by less than a minimum interval.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data after selection-transformation
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    time : ndarray (dtype='float')
        vector with time points
    min_interval : float
        minimum delay between consecutive events, in seconds

    Returns
    -------
    ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    """
    no_merge = time[events[1:, 0] - 1] - time[events[:-1, 2]] >= min_interval

    if no_merge.any():
        begs = concatenate([[events[0, 0]], events[1:, 0][no_merge]])
        ends = concatenate([events[:-1, 2][no_merge], [events[-1, 2]]])

        new_events = vstack((begs, ends)).T
    else:
        new_events = asarray([[events[0, 0], events[-1, 2]]])

    # add the location of the peak in the middle
    new_events = insert(new_events, 1, 0, axis=1)
    for i in new_events:
        i[1] = i[0] + argmax(dat[i[0]:i[2]])

    return new_events


def _wmorlet(f0, sd, sampling_rate, ns=5):
    """
    adapted from nitime

    returns a complex morlet wavelet in the time domain

    Parameters
    ----------
        f0 : center frequency
        sd : standard deviation of frequency
        sampling_rate : samplingrate
        ns : window length in number of standard deviations
    """
    st = 1. / (2. * pi * sd)
    w_sz = float(int(ns * st * sampling_rate))  # half time window size
    t = arange(-w_sz, w_sz + 1, dtype=float) / sampling_rate
    w = (exp(-t ** 2 / (2. * st ** 2)) * exp(2j * pi * f0 * t) /
         sqrt(sqrt(pi) * st * sampling_rate))
    return w


def _realwavelets(s_freq, freqs, dur, width):
    """Create real wavelets, for UCSD.

    Parameters
    ----------
    s_freq : int
        sampling frequency
    freqs : ndarray
        vector with frequencies of interest
    dur : float
        duration of the wavelets in s
    width : float
        parameter controlling gaussian shape

    Returns
    -------
    ndarray
        wavelets
    """
    x = arange(-dur / 2, dur / 2, 1 / s_freq)
    wavelets = empty((len(freqs), len(x)))

    g = exp(-(pi * x ** 2) / width ** 2)

    for i, one_freq in enumerate(freqs):
        y = cos(2 * pi * x * one_freq)
        wavelets[i, :] = y * g

    return wavelets
