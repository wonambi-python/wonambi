"""Module to detect spindles.

"""
from logging import getLogger
lg = getLogger('phypno')
lg.setLevel(10)

from numpy import (absolute, arange, argmax, argmin, asarray, diff, exp, expand_dims, hstack, insert,
                   invert, mean, NaN, ones, pi, power, sqrt, std, vstack, where, zeros)
from scipy.signal import (argrelmax, butter, cheby2, filtfilt, fftconvolve,
                          gaussian, hilbert, welch)

from phypno.graphoelement import Spindles

MAX_FREQUENCY_OF_INTEREST = 50


class DetectSpindle:
    """Design spindle detection on a single channel.

    Parameters
    ----------
    frequency : tuple of float
        low and high frequency of the bandpass filter
    method : str
        method to detect spindles ('hilbert' or 'wavelet')
    method_options : dict
        additional options, depending on method
    threshold : str
        typeof threshold ('absolute', 'relative', 'maxima')
    threshold_options : dict
        additional options, depending on threshold type
    criteria : dict
        additional criteria to apply (see below)

    Notes
    -----
    method_options, with method 'hilbert':
        ... (to be filled with info about filter design)

    method_options, with method 'wavelet':
        - detect_wavelet : dict
            Options to pass to wavelet used for detection (see TimeFreq)
        - detect_smoothing : dict, optional
            - window : str
                window used for smoothing of the wavelet
            - length : float
                length, in s, of window which runs over wavelet
            (if not specified, it doesn't run)
        - select_wavelet : dict, optional
            Options to pass to wavelet used for selection (see TimeFreq)
            (if not specified, uses detection_wavelet)
        - select_smoothing : dict, optional
            (if not specified, uses detection_smoothing)
            - window : str
                window used for smoothing of the wavelet
            - length : float
                length, in s, of window which runs over wavelet

    threshold_options, with threshold 'absolute' or 'relative'""
        - detection_value : float
            the value used for the detection threhsold
        - selection_value : float, optional
            the value used to calculate the start and end of the spindle

    threshold_options, with threshold 'maxima':
        - peak_width : float
            search area in s to identify peaks (the lower, the fewer the peaks)
        - select_width : float
            search area in s before and after a peak to identify beginning and
            end of the spindle

    criteria
        - duration : tuple of float
            minimal and maximal duration in s to be considered a spindle
        - peak_in_fft : dict
            - length : float
                duration of the time window, around the peak, to calculate if
                the peak in the power spectrum falls in the frequency range of
                interest.
            - dryrun : bool, optional (default: False)
                if True, it does not reject spindles, but it only computes fft

    """
    def __init__(self, method='UCSD', frequency=(11, 18),
                 duration=(0.5, 2)):

        self.method = method
        self.frequency = frequency

        if method == 'Ferrarelli2007':
            self.basic = {'data': ('cheby2', ),  # not in the paper
                          'opt': frequency,
                          }
            self.thres = {'data': (None, ),
                          'opt': None,
                          'method': 'std',
                          }
            self.detect = {'data': ('hilbert', 'abs'),
                           'opt': None,
                           'method': 'threshold',
                           'values': 8,
                           }
            self.select = {'method': 'threshold',
                           'values': 3,
                           }
            self.duration = {'values': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'values': 1,
                             'use': False,
                             }

        if method == 'Nir2011':
            # they only selected channels that had enough spindle activity
            self.basic = {'data': ('butter', 'hilbert', 'abs'),
                          'opt': frequency,
                          }
            self.thres = {'data': (None, ),
                          'opt': None,
                          'method': 'mean+std',
                          }
            self.detect = {'data': ('gaussian', ),  # hardly changes anything
                           'opt': 40,
                           'method': 'threshold',
                           'values': 3,
                           }
            self.select = {'method': 'threshold',
                           'values': 1,
                           }
            self.duration = {'values': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'values': 1,
                             'use': False,
                             }

        if method == 'Wamsley2012':
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
                           'values': 4.5,
                           }
            self.select = {'method': None,
                           'values': None,
                           }
            self.duration = {'values': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'values': 2,
                             'use': False,
                             }

        if method == 'UCSD':
            self.basic = {'data': ('morlet', 'abs'),
                          'opt': (mean(frequency), .5),
                          }
            self.thres = {'data': (None, ),
                          'opt': None,
                          'method': None,
                          }
            self.detect = {'data': (None, ),
                           'opt': None,
                           'method': 'peaks',
                           'values': 4
                           }
            self.select = {'method': 'troughs',
                           'values': 1,
                           }
            self.duration = {'values': duration,
                             }
            self.psd_peak = {'method': 'peak',
                             'values': 1,
                             'use': True,
                             }

    def __repr__(self):
        duration = self.duration['values']
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
        from visvis import plot

        all_spindles = []
        chan = 'GR1'  # loop over chan
        lg.info('Detecting spindles on chan %s', chan)
        time = hstack(data.axis['time'])
        dat_orig = hstack(data(chan=chan))

        # basic transformation
        dat_common = transform_signal(dat_orig, data.s_freq,
                                      self.basic['data'], self.basic['opt'])

        if make_plots:
            plot(time, dat_common, ls=':')

        # define thresholds
        dat_thres = transform_signal(dat_common, data.s_freq,
                                     self.thres['data'], self.thres['opt'])
        thres_det, thres_sel = define_thresholds(dat_thres,
                                                 self.thres['method'])

        # detect spindles
        dat_detect = transform_signal(dat_common, data.s_freq,
                                      self.detect['data'], self.detect['opt'])
        if make_plots:
            plot(time, dat_detect)

        if self.detect['method'] == 'peaks':
            det_value = self.detect['values'] * data.s_freq
        elif self.detect['method'] == 'threshold':
            if self.thres['method'] in ('mean', 'std'):
                det_value = self.detect['values'] * thres_det
            if self.thres['method'] in ('mean+std', ):
                det_value = thres_det[0] + self.detect['values'] * thres_det[1]

            lg.debug('Thresholds: detection %f', det_value)
            if make_plots:
                plot((time[0], time[-1]), (det_value, det_value),
                     lc='r', ls='-')

        events = detect_events(dat_detect, self.detect['method'], det_value)

        if events is not None:
            lg.info('Number of potential spindles: %d', events.shape[0])

            # select beginning and end
            if self.select['method'] is None:
                sel_value = None
            elif self.select['method'] == 'troughs':
                sel_value = self.select['values'] * data.s_freq
            elif self.select['method'] == 'threshold':
                if self.thres['method'] in ('mean', 'std'):
                    sel_value = self.select['values'] * thres_sel
                if self.thres['method'] in ('mean+std', ):
                    sel_value = thres_sel[0] + self.select['values'] * thres_sel[1]
                lg.debug('Thresholds: selection %f', sel_value)

            events = select_events(dat_detect, events, self.select['method'],
                                   sel_value)

            # apply criteria: duration
            events = within_duration(events, time, self.duration['values'])
            lg.debug('Number of spindles with good duration: %d',
                    events.shape[0])

            if self.psd_peak['use']:
                peak_limits = self.frequency
            else:
                peak_limits = None

            events = peak_in_power(events, dat_orig, data.s_freq,
                                   self.psd_peak['method'],
                                   self.psd_peak['values'],
                                   peak_limits)

            if make_plots:
                plot(time[events[:, 0]], dat_detect[events[:, 0]],
                     ls=None, ms='>', mc='r')
                plot(time[events[:, 1]], dat_detect[events[:, 1]],
                     ls=None, ms='v', mc='r')
                plot(time[events[:, 2]], dat_detect[events[:, 2]],
                     ls=None, ms='<', mc='r')

            sp_in_chan = make_spindles(events, dat_detect, time)
            lg.info('Number of spindles: %d', len(sp_in_chan))

        else:
            lg.info('No spindle found')
            sp_in_chan = []

        for sp in sp_in_chan:
            sp.update({'chan': chan})
        all_spindles.extend(sp_in_chan)
        # end of loop over chan

        spindle = Spindles()
        spindle.spindle = all_spindles

        return spindle


def transform_signal(dat, s_freq, method, opt=None):
    """

    dat : ndarray
        vector with all the data for one channel
    s_freq : float
        sampling frequency
    method : str
        'cheby2' or 'butter' or 'morlet'
    opt : two float
        if method is 'cheby2' or 'butter', the two frequency bands of interest;
        if method is 'wavelet', the first value is the center frequency, the
        second is the standard deviation in Hz.

    Notes
    -----
    Methods that require optional values are incompatible, because you only
    pass one set of values. We could change that, but the API would become too
    complicated for exceptional cases.

    """
    if 'cheby2' in method:
        N = 4
        Rs = 80
        Wn = asarray(opt) / s_freq
        b, a = cheby2(N, Rs, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)

    if 'butter' in method:
        N = 4
        Wn = asarray(opt) / s_freq
        b, a = butter(N, Wn, btype='bandpass')
        dat = filtfilt(b, a, dat)

    if 'morlet' in method:
        wm = _wmorlet(opt[0], opt[1], s_freq)
        dat = fftconvolve(dat, wm, mode='same')

    if 'hilbert' in method:
        dat = hilbert(dat)

    if 'real' in method:
        dat = dat.real

    if 'abs' in method:
        dat = absolute(dat)

    if 'rms' in method:
        dat = power(dat, 2)
        flat = ones(opt * s_freq)
        dat = sqrt(fftconvolve(dat, flat / sum(flat), mode='same'))

    if 'movingavg' in method:
        flat = ones(opt * s_freq)
        dat = fftconvolve(dat, flat / sum(flat), mode='same')

    if 'gaussian' in method:
        gw = gaussian(s_freq, std=s_freq / opt)
        dat = fftconvolve(dat, gw / sum(gw), mode='same')

    return dat


def define_thresholds(dat, method):
    """Be ready for the case when there are two types of threshold."""

    if method == 'mean':
        thres_det = thres_sel = mean(dat)

    elif method == 'std':
        thres_det = thres_sel = std(dat)

    elif method == 'mean+std':
        """This method returns a tuple, with mean and standard deviation."""
        thres_det = thres_sel = (mean(dat), std(dat))

    elif method is None:
        thres_det = thres_sel = None

    return thres_det, thres_sel


def detect_events(dat, method, value=None):
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
        peaks = argrelmax(dat, order=round(value))[0]
        detected = expand_dims(peaks, axis=1)

    return detected


def select_events(dat, detected, method, value):

    if method == 'threshold':
        above_sel = dat >= value
        detected = _select_period(detected, above_sel)

    elif method == 'troughs':
        detected[:, 0] = detected[:, 1] - value
        detected[:, 2] = detected[:, 1] + value

        good_peaks = (detected[:, 0] >= 0) & (detected[:, 2] < len(dat))
        detected = detected[good_peaks, :].astype(int)

        for i in detected:

            # search minimum before the peak
            i[0] = argmin(dat[i[0]:i[1]]) + i[0]

            # search minimum after the peak
            i[2] = argmin(dat[i[1]:i[2]]) + i[1]

    return detected


def within_duration(events, time, limits):
    min_dur = time[events][:, 2] - time[events][:, 0] >= limits[0]
    max_dur = time[events][:, 2] - time[events][:, 0] <= limits[1]

    return events[min_dur & max_dur, :]


def peak_in_power(events, dat, s_freq, method, value, limits=None):

    dat = diff(dat)  # remove 1/f

    events = insert(events, 3, 0, axis=1)

    if method is not None:
        for i in events:

            if method == 'peak':
                x0 = i[1] - value / 2 * s_freq
                x1 = i[1] + value / 2 * s_freq

            elif method == 'window':
                x0 = i[0]
                x1 = i[1]

            if x0 < 0 or x1 >= len(dat):
                i[3] = NaN  # or zero?

            f, Pxx = welch(dat[x0:x1], s_freq, nperseg=s_freq)
            idx_peak = Pxx[f < MAX_FREQUENCY_OF_INTEREST].argmax()
            i[3] = f[idx_peak]

        if limits is not None:
            in_limits = ((events[:, 3] >= limits[0]) &
                         (events[:, 3] <= limits[1]))
            events = events[in_limits, :]

    return events


def make_spindles(events, dat, time):
    spindles = []
    for i in events:
        one_spindle = {'start_time': time[i[0]],
                       'end_time': time[i[2]],
                       'peak_time': time[i[1]],
                       'peak_val': dat[i[0]],
                       'area_under_curve': sum(dat[i[0]:i[1]]),
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
        2 x N matrix with starting and ending times.

    """
    neg = zeros((1), dtype='bool')
    int_values = asarray(hstack((neg, true_values, neg)), dtype='int')
    cross_threshold = diff(int_values)

    event_starts = where(cross_threshold == 1)[0]
    event_ends = where(cross_threshold == -1)[0]

    if any(event_starts):
        if event_ends[-1] == len(true_values):
            lg.debug('End of the last event is after end of the recording')
            event_ends[-1] -= 1

        events = vstack((event_starts, event_ends)).T

    else:
        events = None

    return events


def _select_period(detected, true_values):
    """For the detected values, we check when it goes below the selection.

    Parameters
    ----------
    detected : ndarray (dtype='int')
        3 x N matrix with starting and ending times.
    true_values : ndarray (dtype='bool')
        array with bool values

    Returns
    -------
    detected : ndarray (dtype='int')
        2 x N matrix with starting and ending times, but these periods are
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
        #TODO: check if accurate
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

    # Finds troughs of the envelope
    envelope_troughs = envelope_samples[where(diffder == 1)[0]]
    envelope_troughs_amp = RectifiedData[envelope_troughs]

    # Determine upper and lower thresholds
    nrem_peaks_index = sleepsamp[envelope_peaks] <= -2
    counts, amps = histogram(envelope_peaks_amp[nrem_peaks_index], 120)  # divide the distribution peaks of the Envelope signal in 120 bins
    maxi = argmax(counts)  # select the most numerous bin
    ampdist_max = amps[maxi]  # peak of the amplitude distribution

    lower_threshold = lower_thresh_ratio * ampdist_max
    upper_threshold = upper_thresh_ratio * mean(RectifiedData[sleepsamp == -2])

    ## Find where peaks are higher/lower than threshold
    below_troughs = envelope_troughs[envelope_troughs_amp < lower_threshold] # lower threshold corresponding to 4* the power of the most numerous bin
    above_peaks = envelope_peaks[envelope_peaks_amp > upper_threshold]

    spistart = zeros(len(above_peaks))  # start of spindle (in 100Hz samples)
    spiend = zeros(len(above_peaks))  # end of spindle (in 100Hz samples)
    spipeak = zeros(len(above_peaks))  # end of spindle (in 100Hz samples)

    nspi = -1  # spindle count
    # for all indexes of peaks (peaks of peaks)
    i = 0
    while i < len(above_peaks):

        current_peak = above_peaks[i]

        # find troughs before and after current peak
        trough_before = below_troughs[where((below_troughs > 1) & (below_troughs < current_peak))[0][-1]]
        trough_after  = below_troughs[where((below_troughs < len(RectifiedData)) & (below_troughs > current_peak))[0][0]]

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

from phypno import Dataset
from phypno.attr import Scores

d = Dataset('/home/gio/recordings/MG72/eeg/raw/xltek/MG72_eeg_xltek_sessA_d09_07_47_00')


score = Scores('/home/gio/recordings/MG72/doc/scores/MG72_eeg_xltek_sessA_d09_07_47_00_scores.xml')
N2_sleep = score.get_epochs(('NREM2', 'NREM3'))

start_time = [x['start_time'] for x in N2_sleep]
end_time = [x['end_time'] for x in N2_sleep]

data = d.read_data(chan=['GR1', 'GR2'],
                   begtime=start_time,
                   endtime=end_time)


HP_FILTER = 1
LP_FILTER = 40
from phypno.trans import Filter
hp_filt = Filter(low_cut=HP_FILTER, s_freq=data.s_freq)
lp_filt = Filter(high_cut=LP_FILTER, s_freq=data.s_freq)
data = lp_filt(hp_filt(data))

self = DetectSpindle(method='Wamsley2012')
self.detect['values'] = 3
sp = self(data, True)
[x['peak_freq'] for x in sp.spindle]
