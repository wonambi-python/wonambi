"""Module to detect spindles.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import (absolute, arange, argmax, argmin, asarray, cos, diff, exp, empty,
                   hstack, insert, invert, linspace, mean, median, nan, ones, pi,
                   sqrt, std, vstack, where, zeros)
from scipy.signal import (argrelmax, butter, cheby2, filtfilt, fftconvolve,
                          hilbert, periodogram, welch)

from phypno.graphoelement import Spindles

MAX_FREQUENCY_OF_INTEREST = 50


class DetectSpindle:
    """Design spindle detection on a single channel.

    Parameters
    ----------
    method : str
        one of the predefined methods (see below 'housestyle')
    frequency : tuple of float
        low and high frequency of spindle band
    duration : tuple of float
        min and max duration of spindles

    """
    def __init__(self, method='UCSD', frequency=None, duration=None):

        if frequency is None:
            frequency = (11, 18)
        if duration is None:
            duration = (0.5, 2)

        self.method = method
        self.frequency = frequency
        self.duration = duration


        if method == 'Ferrarelli2007':
            self.det_cheby2 = {'order': 4,
                               'freq': self.frequency,
                               }
            self.det_thresh = 8
            self.sel_thresh = 3

        elif method == 'Nir2011':
            self.det_butter = {'order': 4,
                               'freq': self.frequency,
                               }
            self.det_thresh = 3
            self.moving_avg = {'dur':  .4}
            self.sel_thresh = 1

        elif method == 'Wamsley2012':
            self.det_wavelet = {'f0': mean(self.frequency),
                                'sd': .5,
                                'dur': 2,
                                }
            self.det_thresh = 4.5
            self.moving_avg = {'dur': .1}
            self.sel_thresh = nan  # necessary for gui/detect

        elif method == 'UCSD':
            self.det_wavelet = {'freqs': arange(frequency[0],
                                                frequency[1] + .5, .5),
                                'dur': 1,
                                'width': .5,
                                'win': .5,
                                }
            self.det_thresh = .5  # wavelet_peak_thresh
            self.sel_wavelet = {'freqs': arange(frequency[0],
                                                frequency[1] + .5, .5),
                                'dur': 1,
                                'width': .2,
                                'win': .2,
                                }
            self.sel_thresh = .2
            self.ratio_thresh = .5
        else:
            raise ValueError('Unknown method')

    def __repr__(self):
        return ('detsp_{0}_{1:02}-{2:02}Hz_{3:04.1f}-{4:04.1f}s'
                ''.format(self.method, self.frequency[0], self.frequency[1],
                          self.duration[0], self.duration[1]))

    def __call__(self, data, make_plots=False):
        """Detect spindles on the data.

        Parameters
        ----------
        data : instance of Data
            data used for detection

        Returns
        -------
        instance of graphoelement.Spindles
            description of the detected spindles

        """
        spindle = Spindles()
        spindle.chan_name = data.axis['chan'][0]
        spindle.det_value = zeros(data.number_of('chan')[0])
        spindle.sel_value = zeros(data.number_of('chan')[0])

        all_spindles = []
        for i, chan in enumerate(data.axis['chan'][0]):
            lg.info('Detecting spindles on chan %s', chan)
            time = hstack(data.axis['time'])
            dat_orig = hstack(data(chan=chan))

            if self.method == 'Ferrarelli2007':
                sp_in_chan, values = detect_Ferrarelli2007(dat_orig,
                                                           data.s_freq, time,
                                                           self)

            elif self.method == 'Nir2011':
                sp_in_chan, values = detect_Nir2011(dat_orig, data.s_freq,
                                                    time, self)

            elif self.method == 'Wamsley2012':
                sp_in_chan, values = detect_Wamsley2012(dat_orig, data.s_freq,
                                                        time, self)

            elif self.method == 'UCSD':
                sp_in_chan, values = detect_UCSD(dat_orig, data.s_freq, time,
                                                 self)
            else:
                raise ValueError('Unknown method')

            spindle.det_value[i] = values['det_value']
            spindle.sel_value[i] = values['sel_value']
            for sp in sp_in_chan:
                sp.update({'chan': chan})
            all_spindles.extend(sp_in_chan)
            # end of loop over chan

        spindle.spindle = sorted(all_spindles, key=lambda x: x['start_time'])

        return spindle


def detect_Ferrarelli2007(dat_orig, s_freq, time, opts):
    """Ferrarelli, F. et al. Am. J. Psychiatry 164, 483-92 (2007).

    """

    dat_det = transform_signal(dat_orig, s_freq, 'cheby2', opts.det_cheby2)
    det_value = define_threshold(dat_det, s_freq, 'threshold_mean+std',
                                 opts.det_thresh)
    sel_value = define_threshold(dat_det, s_freq, 'threshold_mean+std',
                                 opts.sel_thresh)

    dat_det = transform_signal(dat_det, s_freq, 'hilbert')
    dat_det = transform_signal(dat_det, s_freq, 'abs')

    events = detect_events(dat_det, 'threshold', det_value)

    if events is not None:
        events = select_events(dat_det, events, 'threshold', sel_value)

        events = within_duration(events, time, opts.duration)

        sp_in_chan = make_spindles(events, dat_det, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value': det_value, 'sel_value': sel_value}

    return sp_in_chan, values


def detect_Nir2011(dat_orig, s_freq, time, opts):
    """Nir, Y. et al. Neuron 70, 153-69 (2011).

    This paper also selects channels carefully:
    'First, the channels with spindle activity in NREM sleep were
    chosen for further analysis.'

    'Third, those channels, in which an increase in spectral power
    within the detected events was restricted to the spindle-frequency
    range (10-16 Hz) rather than broadband.'

    """
    dat_det = transform_signal(dat_orig, s_freq, 'butter', opts.det_butter)
    det_value = define_threshold(dat_det, s_freq, 'threshold_mean+std',
                                 opts.det_thresh)
    sel_value = define_threshold(dat_det, s_freq, 'threshold_mean+std',
                                 opts.sel_thresh)

    dat_det = transform_signal(dat_det, s_freq, 'hilbert')
    dat_det = transform_signal(dat_det, s_freq, 'abs')
    dat_det = transform_signal(dat_det, s_freq, 'moving_avg', opts.moving_avg)

    events = detect_events(dat_det, 'threshold', det_value)

    if events is not None:
        events = select_events(dat_det, events, 'threshold', sel_value)

        events = within_duration(events, time, opts.duration)

        sp_in_chan = make_spindles(events, dat_det, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value': det_value, 'sel_value': sel_value}

    return sp_in_chan, values


def detect_Wamsley2012(dat_orig, s_freq, time, opts):
    """Wamsley, E. J. et al. Biol. Psychiatry 71, 154-61 (2012).

    """
    dat_det = transform_signal(dat_orig, s_freq, 'morlet', opts.det_wavelet)
    dat_det = transform_signal(dat_det, s_freq, 'abs')

    det_value = define_threshold(dat_det, s_freq, 'threshold_mean',
                                 opts.det_thresh)

    dat_det = transform_signal(dat_det, s_freq, 'moving_avg', opts.moving_avg)

    events = detect_events(dat_det, 'threshold', det_value)

    if events is not None:
        events = within_duration(events, time, opts.duration)

        sp_in_chan = make_spindles(events, dat_det, time, s_freq)

    else:
        lg.info('No spindle found')
        sp_in_chan = []

    values = {'det_value': det_value, 'sel_value': nan}

    return sp_in_chan, values


def detect_UCSD(dat_orig, s_freq, time, opts):

    dat_det = transform_signal(dat_orig, s_freq, 'wavelet_real',
                               opts.det_wavelet)

    det_value = define_threshold(dat_det, s_freq, 'threshold_median+std',
                                 opts.det_thresh)

    events = detect_events(dat_det, 'maxima', det_value)

    dat_sel = transform_signal(dat_orig, s_freq, 'wavelet_real',
                               opts.sel_wavelet)
    sel_value = define_threshold(dat_sel, s_freq, 'threshold_median+std',
                                 opts.sel_thresh)
    events = select_events(dat_sel, events, 'threshold', sel_value)

    events = within_duration(events, time, opts.duration)

    events = power_ratio(events, dat_orig, s_freq, opts.frequency,
                         opts.ratio_thresh)

    sp_in_chan = make_spindles(events, dat_det, time, s_freq)

    values = {'det_value': det_value, 'sel_value': sel_value}

    return sp_in_chan, values


def transform_signal(dat, s_freq, method, method_opt=None):
    """Transform the data using different methods.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with all the data for one channel
    s_freq : float
        sampling frequency
    method : str
        one of 'cheby2', 'butter', 'morlet', 'morlet_real', 'hilbert', 'abs',
        'moving_avg'
    method_opt : dict
        depends on methods

    Returns
    -------
    ndarray (dtype='float')
        vector with all the data for one channel

    Notes
    -----
    Wavelets pass only absolute values already, it does not make sense to store
    the complex values.

    Methods
    -------
    cheby2 has parameters:
        freq : tuple of float
            high and low values for bandpass
        order : int
            filter order

    butter has parameters:
        freq : tuple of float
            high and low values for bandpass
        order : int
            filter order

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

    """
    if 'cheby2' == method:
        freq = method_opt['freq']
        N = method_opt['order']

        Rs = 80
        nyquist = s_freq / 2
        Wn = asarray(freq) / nyquist
        b, a = cheby2(N, Rs, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)

    if 'butter' == method:
        freq = method_opt['freq']
        N = method_opt['order']

        nyquist = s_freq / 2
        Wn = asarray(freq) / nyquist
        b, a = butter(N, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)

    if 'morlet' == method:
        f0 = method_opt['f0']
        sd = method_opt['sd']
        dur = method_opt['dur']

        wm = _wmorlet(f0, sd, s_freq, dur)
        dat = absolute(fftconvolve(dat, wm, mode='same'))

    if 'wavelet_real' == method:
        freqs = method_opt['freqs']
        dur = method_opt['dur']
        width = method_opt['width']
        win = method_opt['win'] * s_freq

        wm = _realwavelets(s_freq, freqs, dur, width)
        tfr = empty((dat.shape[0], wm.shape[0]))
        for i, one_wm in enumerate(wm):
            x = abs(fftconvolve(dat, one_wm, mode='same'))
            tfr[:, i] = fftconvolve(x, tukeywin(win), mode='same')
        dat = mean(tfr, axis=1)

    if 'hilbert' == method:
        dat = hilbert(dat)

    if 'abs' == method:
        dat = absolute(dat)

    if 'moving_avg' == method:
        dur = method_opt['dur']

        flat = ones(dur * s_freq)
        dat = fftconvolve(dat, flat / sum(flat), mode='same')

    return dat


def define_threshold(dat, s_freq, method, value):
    """Return the value of the threshold based on relative values.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data after selection-transformation
    method : str

    """

    if method in ('maxima', 'minima'):
        value = value * s_freq
    elif method == 'threshold_mean':
        value = value * mean(dat)
    elif method == 'threshold_median':
        value = value * median(dat)
    elif method == 'threshold_std':
        value = value * mean(dat)
    elif method == 'threshold_mean+std':
        value = mean(dat) + value * std(dat)
    elif method == 'threshold_median+std':
        value = median(dat) + value * std(dat)

    return value


def detect_events(dat, method, value=None):
    """Detect events using 'threshold' or 'maxima' method.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data after selection-transformation
    method : str
        'threshold' or 'maxima'
    value : float
        for 'threshold', it's the value of threshold for the event detection
        for 'maxima', it's the distance in s from the peak to find a minimum

    Returns
    -------
    ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples

    """
    if method == 'threshold':
        above_det = dat >= value
        detected = _detect_start_end(above_det)

        if detected is None:
            return None

        # add the location of the peak in the middle
        detected = insert(detected, 1, 0, axis=1)
        for i in detected:
            i[1] = i[0] + argmax(dat[i[0]:i[2]])

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
        'threshold'
    value : float
        for 'threshold', it's the value of threshold for the spindle selection.

    Returns
    -------
    ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples

    """
    if method == 'threshold':
        above_sel = dat >= value
        detected = _select_period(detected, above_sel)

    return detected


def within_duration(events, time, limits):
    """Check whether spindle is within time limits.

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
        N x 3 matrix with start, peak, end samples

    """
    min_dur = time[events[:, 2] - 1] - time[events[:, 0]] >= limits[0]
    max_dur = time[events[:, 2] - 1] - time[events[:, 0]] <= limits[1]

    return events[min_dur & max_dur, :]


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


def peak_in_power(events, dat, s_freq, method, value=None, limits=None):
    """Define peak in power of the signal.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
    dat : ndarray (dtype='float')
        vector with the original data
    s_freq : float
        sampling frequency
    method : str
        'peak' or 'interval'
    value : float
        size of the window around peak, or nothing (for 'interval')
    limits : tuple of float
        if not None, keep only spindles with psd peak within limits

    Returns
    -------
    ndarray (dtype='int')
        N x 4 matrix with start, peak, end samples, and peak frequency

    """
    dat = diff(dat)  # remove 1/f

    events = insert(events, 3, 0, axis=1)

    if method is not None:
        for i in events:

            if method == 'peak':
                x0 = i[1] - value / 2 * s_freq
                x1 = i[1] + value / 2 * s_freq

            elif method == 'interval':
                x0 = i[0]
                x1 = i[2]

            if x0 < 0 or x1 >= len(dat):
                i[3] = 0  # you cannot use NaN in int numpy
            else:
                f, Pxx = welch(dat[x0:x1], s_freq, nperseg=s_freq)
                idx_peak = Pxx[f < MAX_FREQUENCY_OF_INTEREST].argmax()
                i[3] = f[idx_peak]

        if limits is not None:
            in_limits = ((events[:, 3] >= limits[0]) &
                         (events[:, 3] <= limits[1]))
            events = events[in_limits, :]

    return events


def make_spindles(events, dat, time, s_freq):
    """Create dict for each spindle, based on events of time points.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 4 matrix with start, peak, end samples, and peak frequency
    dat : ndarray (dtype='float')
        vector with the data after detection-transformation (to compute peak)
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
    spindles = []
    for i in events:
        if len(i) == 4:
            peak_freq = i[3]
        else:
            peak_freq = nan
        one_spindle = {'start_time': time[i[0]],
                       'end_time': time[i[2]],
                       'peak_time': time[i[1]],
                       'peak_val': dat[i[1]],
                       'area_under_curve': sum(dat[i[0]:i[2]]) / s_freq,
                       'peak_freq': peak_freq,
                       }
        spindles.append(one_spindle)

    return spindles


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
    int_values = asarray(hstack((neg, true_values, neg)), dtype='int')
    cross_threshold = diff(int_values)

    event_starts = where(cross_threshold == 1)[0]
    event_ends = where(cross_threshold == -1)[0]

    if len(event_starts):
        events = vstack((event_starts, event_ends)).T

    else:
        events = None

    return events


def _select_period(detected, true_values):
    """For the detected values, we check when it goes below the selection.

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
        # get the first time point when it goes above selection thres
        start_sel = where(true_values[:one_spindle[0]])[0]
        if start_sel.any():
            one_spindle[0] = start_sel[-1]

        # get the last time point when it stays above selection thres
        end_sel = where(true_values[one_spindle[2]:])[0] - 1
        if end_sel.any():
            one_spindle[2] += end_sel[0]

    return detected


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
    x = arange(-dur/2, dur/2, 1/s_freq)
    wavelets = empty((len(freqs), len(x)))

    g = exp(-(pi * x ** 2) / width ** 2)

    for i, one_freq in enumerate(freqs):
        y = cos(2 * pi * x * one_freq)
        wavelets[i, :] = y * g

    return wavelets


def tukeywin(window_length, alpha=0.5):
    """Taken from http://leohart.wordpress.com/2006/01/29/hello-world/ """
    x = linspace(0, 1, window_length)
    w = ones(x.shape)

    # first condition 0 <= x < alpha/2
    first_condition = x < alpha / 2
    w[first_condition] = 0.5 * (1 + cos(2 * pi / alpha *
                                        (x[first_condition] - alpha / 2)))

    # second condition already taken care of

    # third condition 1 - alpha / 2 <= x <= 1
    third_condition = x >= (1 - alpha / 2)
    w[third_condition] = 0.5 * (1 + cos(2 * pi / alpha *
                                        (x[third_condition] - 1 + alpha / 2)))

    return w / len(w)

"""
def ferrarelli_spindle_detection(data):
    \"""Data can be one channel at the time.

    Remember to add duration criteria at the end, DURATION BETWEEN 0.3 and 3

    one channel at the time
    \"""
    lower_thresh_ratio = 2
    upper_thresh_ratio = 5
    new_freq = 100

    chan = data.axis['chan'][0][0]

    # resample data
    time_0 = data.axis['time'][0][0]
    time_1 = data.axis['time'][-1][-1]
    n_samples = (time_1 - time_0) * new_freq + 1
    dat = zeros(n_samples)  # zero padding between epochs
    sleepsamp = zeros(n_samples)

    for one_trial in iter(data):
        smp_0 = (one_trial.axis['time'][0][0] - time_0) * new_freq
        smp_1 = (one_trial.axis['time'][0][-1] - time_0) * new_freq + 1
        sleepsamp[smp_0:smp_1] = -2
        dat[smp_0:smp_1] = resample(one_trial(trial=0, chan=chan),  # TODO: remove chan or something like that
                                    one_trial.number_of('time')[0] /
                                    one_trial.s_freq * new_freq)


    # Bandpass filter from 11-15 Hz and rectify filtered signal
    BandFilteredData = bandpass_filter_ferrarelli(dat, data.s_freq)
    RectifiedData = abs(BandFilteredData)

    # Create envelope from the peaks of rectified signal (peaks found using zero-crossing of the derivative)
    datader = diff(RectifiedData)  # x(2)-x(1), x(3)-x(2), ... + at increase, - at decrease
    posder = zeros(len(datader))
    posder[datader > 0] = 1 # index of all points at which the rectified signal is increasing in amplitude
    diffder = diff(posder)  # -1 going from increase to decrease, 1 going from decrease to increase, 0 no change
    envelope_samples = where(diffder == -1)[0]  # peak index of rectified signal
    Envelope = RectifiedData[envelope_samples]  # peak amplitude of rectified signal

    # Finds peaks of the envelope
    datader = diff(Envelope)
    posder = zeros(len(datader))
    posder[datader > 0] = 1  # index of all points at which the rectified signal is increasing in amplitude
    diffder = diff(posder)
    envelope_peaks = envelope_samples[where(diffder == -1)[0]]
    envelope_peaks_amp = RectifiedData[envelope_peaks] # peak amplitude of Envelope signal

    # Finds minima of the envelope
    envelope_minima = envelope_samples[where(diffder == 1)[0]]
    envelope_minima_amp = RectifiedData[envelope_minima]

    # Determine upper and lower thresholds
    nrem_peaks_index = sleepsamp[envelope_peaks] <= -2
    counts, amps = histogram(envelope_peaks_amp[nrem_peaks_index], 120)  # divide the distribution peaks of the Envelope signal in 120 bins
    maxi = argmax(counts)  # select the most numerous bin
    ampdist_max = amps[maxi]  # peak of the amplitude distribution

    lower_threshold = lower_thresh_ratio * ampdist_max
    upper_threshold = upper_thresh_ratio * mean(RectifiedData[sleepsamp == -2])

    ## Find where peaks are higher/lower than threshold
    below_minima = envelope_minima[envelope_minima_amp < lower_threshold] # lower threshold corresponding to 4* the power of the most numerous bin
    above_peaks = envelope_peaks[envelope_peaks_amp > upper_threshold]

    spistart = zeros(len(above_peaks))  # start of spindle (in 100Hz samples)
    spiend = zeros(len(above_peaks))  # end of spindle (in 100Hz samples)
    spipeak = zeros(len(above_peaks))  # end of spindle (in 100Hz samples)

    nspi = -1  # spindle count
    # for all indexes of peaks (peaks of peaks)
    i = 0
    while i < len(above_peaks):

        current_peak = above_peaks[i]

        # find minima before and after current peak
        trough_before = below_minima[where((below_minima > 1) & (below_minima < current_peak))[0][-1]]
        trough_after  = below_minima[where((below_minima < len(RectifiedData)) & (below_minima > current_peak))[0][0]]

        if True: #TODO: ~isempty(trough_before) && ~isempty(trough_after)  % only count spindle if it has a start and end
            nspi += 1
            spistart[nspi] = trough_before
            spiend[nspi] = trough_after
            # if there are multiple peaks, pick the highest and skip the rest
            potential_peaks = above_peaks[(above_peaks > trough_before) & (above_peaks < trough_after)]
            maxpki = argmax(RectifiedData[potential_peaks])
            current_peak = potential_peaks[maxpki]
            spipeak[nspi] = current_peak

            i = i + len(potential_peaks)  # adjust the index to account for different max
        else:
            i = i + 1

    #TODO: spistart = spistart(isnan(spistart) ~= 1)
    #TODO: spiend = spiend(isnan(spiend) ~= 1)

    all_spindles = []
    for i in range(nspi + 1):
        one_spindle = {'start_time': time_0 + spistart[i] / new_freq,
                       'end_time': time_0 + spiend[i] / new_freq,
                       'peak_time': time_0 + spipeak[i] / new_freq,
                       'peak_val': RectifiedData[spipeak[i]],  # TODO: not sure
                       'area_under_curve': sum(RectifiedData[spistart[i]:spiend[i]]),  # TODO: I don't know
                       'chan': chan,
                       }
        all_spindles.append(one_spindle)

    return all_spindles

"""
