"""Module to detect spindles.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import (absolute, arange, argmax, argmin, asarray, diff, exp, empty,
                   expand_dims, hstack, insert, invert, mean, median, ones, pi,
                   power, sqrt, std, vstack, where, zeros)
from scipy.signal import (argrelmax, butter, cheby2, filtfilt, fftconvolve,
                          gaussian, hilbert, welch)

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

    Notes
    -----
    The possible methods are:
       - 'housestyle': hilbert envelope after bandpass filtering and detection
                       based on maxima
       -


    If you want to create your own detection method, this is the pipeline:

                   Detection Threshold
                  /               \
             BASIC--Transform--DETECT--Events
            /     \                      \
        ORIG       \---Transform--------SELECT----Long Events
            \       \                   /               |
             \       Selection Threshold                |
              \                                 Duration Criteria
               \                                        |
                \--------------------------------------PSD----> SPINDLES

    with
        basic['data'] : transformations for futher processing and thresholds
        basic['opt'] : options for above
        detect['method'] : method to detect spindles ('maxima',
                           'threshold_mean', 'threshold_std' or
                           'threshold_mean+std')
        detect['value'] : for threshold, one value to multiply the threshold;
                          for maxima, how many peaks it finds in s
        detect['data'] : transformations only for detection (not for threshold)
                         these data are used for peak values and area under
                         curve
        detect['opt'] : options for above
        select['method'] : method to detect spindles ('minima',
                           'threshold_mean', 'threshold_std' or
                           'threshold_mean+std')
        select['value'] : for threshold, one value to multiply the threshold;
                          for minima, how long the window to detect minima in s
        select['data'] : transformations only for selection (not for threshold)
        select['opt'] : options for above
        duration['value'] : tuple of float for min and max duration
        psd_peak['method'] : 'peak' (predefined period around the maximum
                             value) or 'interval' (only the data in the
                             selection window)
        psd_peak['value'] : for 'peak', the length of window around peak
        psd_peak['use'] : if it's used to remove spindles

    """
    def __init__(self, method='housestyle', frequency=None, duration=None):

        if frequency is None:
            frequency = (11, 18)
        if duration is None:
            duration = (0.5, 2)

        self.method = method
        self.frequency = frequency

        if method == 'housestyle':
            self.basic = {'data': ('cheby2', 'hilbert', 'abs'),
                          'opt': (frequency, None, None),
                          }
            self.detect = {'method': 'maxima',
                           'value': 3,
                           'data': (None, ),
                           'opt': (None, ),
                           }
            self.select = {'method': 'minima',
                           'value': 1,
                           'data': (None, ),
                           'opt': (None, ),
                           }
            self.duration = {'value': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'value': 1,
                             'use': True,
                             }

        if method == 'Nir2011':
            """Nir, Y. et al. Neuron 70, 153-69 (2011).

            This paper also selects channels carefully:
            'First, the channels with spindle activity in NREM sleep were
            chosen for further analysis.'

            'Third, those channels, in which an increase in spectral power
            within the detected events was restricted to the spindle-frequency
            range (10-16 Hz) rather than broadband.'

            """
            self.basic = {'data': ('butter', ),
                          'opt': (frequency, ),
                          }
            self.detect = {'method': 'threshold_mean+std',
                           'value': 3,
                           'data': ('hilbert', 'abs', 'gaussian'),
                           'opt': (None, None, 40),
                           }
            self.select = {'method': 'threshold_mean+std',
                           'value': 1,
                           'data': ('hilbert', 'abs', 'gaussian'),
                           'opt': (None, None, 40),
                           }
            self.duration = {'value': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'value': 1,
                             'use': False,
                             }

        if method == 'Wamsley2012':
            """Wamsley, E. J. et al. Biol. Psychiatry 71, 154-61 (2012).

            """
            self.basic = {'data': ('morlet', 'abs'),
                          'opt': (mean(frequency), .5),
                          }
            self.thres = {'data': ('movingavg', ),
                          'opt': 0.1,
                          'method': 'mean',
                          }
            self.detect = {'data': ('movingavg', ),
                           'opt': 0.1,
                           'method': 'threshold',
                           'value': 4.5,
                           }
            self.select = {'method': None,
                           'value': None,
                           }
            self.duration = {'value': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'value': 2,
                             'use': False,
                             }

        if method == 'Ferrarelli2007':
            """Ferrarelli, F. et al. Am. J. Psychiatry 164, 483-92 (2007).

            """
            self.basic = {'data': ('cheby2', ),  # not in the paper
                          'opt': (frequency, ),
                          }
            self.detect = {'method': 'threshold_std',
                           'value': 8,
                           'data': ('hilbert', 'abs'),
                           'opt': None,
                           }
            self.select = {'method': 'threshold_std',
                           'value': 3,
                           'data': ('hilbert', 'abs'),
                           'opt': None,
                           }
            self.duration = {'value': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'value': 1,
                             'use': False,
                             }

        if method == 'UCSD':
            self.basic = {'data': ('morlet_interval', ),
                          'opt': (frequency, ),  # frequency (8, 16)
                          }
            self.detect = {'method': 'threshold_median+std',
                           'value': 0.5,
                           'data': (None, ),
                           'opt': None,
                           }
            self.select = {'method': 'minima',
                           'value': 1,
                           'data': (None, ),
                           'opt': None,
                           }
            self.duration = {'value': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'value': 1,
                             'use': True,
                             }

    def __repr__(self):
        duration = self.duration['value']
        _repr = ('detsp_{0}_{1:02}-{2:02}Hz_{3:04.1f}-{4:04.1f}s'
                 ''.format(self.method, self.frequency[0], self.frequency[1],
                           duration[0], duration[1]))
        return _repr

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
        if make_plots:
            from visvis import plot

        spindle = Spindles()
        spindle.chan_name = data.axis['chan'][0]
        spindle.mean = zeros(data.number_of('chan')[0])
        spindle.std = zeros(data.number_of('chan')[0])
        spindle.det_value = zeros(data.number_of('chan')[0])
        spindle.sel_value = zeros(data.number_of('chan')[0])

        all_spindles = []
        for i, chan in enumerate(data.axis['chan'][0]):
            lg.info('Detecting spindles on chan %s', chan)
            time = hstack(data.axis['time'])
            dat_orig = hstack(data(chan=chan))

            # basic transformation
            dat_common = transform_signal(dat_orig, data.s_freq,
                                          self.basic['data'],
                                          self.basic['opt'])

            if make_plots:
                plot(time, dat_common, ls=':')

            # DETECTION: define threshold
            det_value = define_threshold(dat_common, data.s_freq,
                                         self.detect['method'],
                                         self.detect['value'])
            spindle.det_value[i] = det_value

            # DETECTION
            dat_detect = transform_signal(dat_common, data.s_freq,
                                          self.detect['data'],
                                          self.detect['opt'])
            events = detect_events(dat_detect, self.detect['method'],
                                   det_value)

            spindle.mean[i] = mean(dat_detect)
            spindle.std[i] = std(dat_detect)

            sel_value = None
            if events is not None:
                lg.info('Number of potential spindles: %d', events.shape[0])

                # SELECTION: define threshold
                sel_value = define_threshold(dat_common, data.s_freq,
                                             self.select['method'],
                                             self.select['value'])
                spindle.sel_value[i] = sel_value

                # SELECTION
                dat_select = transform_signal(dat_common, data.s_freq,
                                              self.select['data'],
                                              self.select['opt'])
                events = select_events(dat_select, events,
                                       self.select['method'], sel_value)

                # apply criteria: duration
                events = within_duration(events, time, self.duration['value'])
                lg.debug('Number of spindles with good duration: %d',
                         events.shape[0])

                if self.psd_peak['use']:
                    peak_limits = self.frequency
                else:
                    peak_limits = None

                events = peak_in_power(events, dat_orig, data.s_freq,
                                       self.psd_peak['method'],
                                       self.psd_peak['value'],
                                       peak_limits)

                if make_plots:
                    plot(time[events[:, 0]], dat_detect[events[:, 0]],
                         ls=None, ms='>', mc='r')
                    plot(time[events[:, 1]], dat_detect[events[:, 1]],
                         ls=None, ms='v', mc='r')
                    plot(time[events[:, 2]], dat_detect[events[:, 2]],
                         ls=None, ms='<', mc='r')

                sp_in_chan = make_spindles(events, dat_detect, time,
                                           data.s_freq)
                lg.info('Number of spindles: %d', len(sp_in_chan))

            else:
                lg.info('No spindle found')
                sp_in_chan = []

            for sp in sp_in_chan:
                sp.update({'chan': chan})
            all_spindles.extend(sp_in_chan)
            # end of loop over chan

        spindle.spindle = sorted(all_spindles, key=lambda x: x['start_time'])

        return spindle


def transform_signal(dat, s_freq, method, opt=None):
    """Transform the data using different methods.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with all the data for one channel
    s_freq : float
        sampling frequency
    method : tuple of str
        'cheby2' or 'butter' or 'morlet'
    opt : tuple of values
        if method is 'cheby2' or 'butter', the two frequency bands of interest;
        if method is 'wavelet', the first value is the center frequency, the
        second is the standard deviation in Hz.

    Returns
    -------
    ndarray (dtype='float')
        vector with all the data for one channel

    Notes
    -----
    Wavelets pass only absolute values already, it does not make sense to store
    the complex values.

    order is hard-coded

    """
    if 'cheby2' in method:
        method_opt = opt[method.index('cheby2')]
        N = 4
        Rs = 80
        nyquist = s_freq / 2
        Wn = asarray(method_opt) / nyquist
        b, a = cheby2(N, Rs, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)

    if 'butter' in method:
        method_opt = opt[method.index('butter')]
        N = 4
        nyquist = s_freq / 2
        Wn = asarray(method_opt) / nyquist
        b, a = butter(N, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)

    if 'morlet' in method:
        method_opt = opt[method.index('morlet')]
        wm = _wmorlet(method_opt[0], method_opt[1], s_freq)
        dat = absolute(fftconvolve(dat, wm, mode='same'))

    if 'morlet_interval' in method:
        method_opt = opt[method.index('morlet_interval')]

        from phypno.trans.frequency import _create_morlet
        method_opt = arange(method_opt[0], method_opt[1])
        # with a w of 10, mimic the wavelet of UCSD script
        wm = _create_morlet(method_opt, s_freq, {'w': 10, 'M_in_s': 1})
        tfr = empty((dat.shape[0], wm.shape[0]))
        for i, one_wm in enumerate(wm):
            tfr[:, i] = absolute(fftconvolve(dat, one_wm, mode='same'))
        dat = mean(tfr, axis=1)

    if 'hilbert' in method:
        dat = hilbert(dat)

    if 'real' in method:
        dat = dat.real

    if 'abs' in method:
        dat = absolute(dat)

    if 'rms' in method:
        method_opt = opt[method.index('rms')]
        dat = power(dat, 2)
        flat = ones(method_opt * s_freq)
        dat = sqrt(fftconvolve(dat, flat / sum(flat), mode='same'))

    if 'moving_avg' in method:
        method_opt = opt[method.index('moving_avg')]
        flat = ones(method_opt * s_freq)
        dat = fftconvolve(dat, flat / sum(flat), mode='same')

    if 'gaussian' in method:
        method_opt = opt[method.index('gaussian')]
        gw = gaussian(s_freq, std=s_freq / method_opt)
        dat = fftconvolve(dat, gw / sum(gw), mode='same')

    return dat


def define_threshold(dat, s_freq, method, value):
    """Be ready for the case when there are two types of threshold."""

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
    if method[:10] == 'threshold_':
        above_det = dat >= value
        detected = _detect_start_end(above_det)

        if detected is None:
            return None

        # add the location of the peak in the middle
        detected = insert(detected, 1, 0, axis=1)
        for i in detected:
            i[1] = i[0] + argmax(dat[i[0]:i[2]])

    if method == 'maxima':
        peaks = argrelmax(dat, order=round(value))[0]
        detected = expand_dims(peaks, axis=1)

    return detected


def select_events(dat, detected, method, value):
    """Select duration of the events.

    Parameters
    ----------
    dat : ndarray (dtype='float')
        vector with the data after selection-transformation
    detected : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples


    """
    if method == 'threshold':
        above_sel = dat >= value
        detected = _select_period(detected, above_sel)

    elif method == 'minima':
        beg_trough = detected - value
        end_trough = detected + value

        detected = hstack((beg_trough, detected, end_trough))

        good_peaks = (detected[:, 0] >= 0) & (detected[:, 2] < len(dat))
        detected = detected[good_peaks, :].astype(int)

        for i in detected:

            # search minimum before the peak
            i[0] = argmin(dat[i[0]:i[1]]) + i[0]

            # search minimum after the peak
            i[2] = argmin(dat[i[1]:i[2]]) + i[1]

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


def peak_in_power(events, dat, s_freq, method, value, limits=None):
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
        one_spindle = {'start_time': time[i[0]],
                       'end_time': time[i[2]],
                       'peak_time': time[i[1]],
                       'peak_val': dat[i[1]],
                       'area_under_curve': sum(dat[i[0]:i[2]]) / s_freq,
                       'peak_freq': i[3],
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

    """
    true_values = invert(true_values)

    for one_spindle in detected:
        # get the first time point when it goes above selection thres
        start_sel = where(true_values[:one_spindle[0]])[0]
        if start_sel.any():
            one_spindle[0] = start_sel[-1]

        # get the last time point when it stays above selection thres
        # TODO: check if accurate
        end_sel = where(true_values[one_spindle[2]:])[0]
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

    TODO: compare with scipy. However, this wavelet has sd

    """
    st = 1. / (2. * pi * sd)
    w_sz = float(int(ns * st * sampling_rate))  # half time window size
    t = arange(-w_sz, w_sz + 1, dtype=float) / sampling_rate
    w = (exp(-t ** 2 / (2. * st ** 2)) * exp(2j * pi * f0 * t) /
         sqrt(sqrt(pi) * st * sampling_rate))
    return w


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
