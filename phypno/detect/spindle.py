"""Module to detect spindles.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import (arange, argmin, asarray, diff, hstack, invert,
                   ones, vstack, where, zeros)
from scipy.signal import welch, argrelmax

from ..trans import Filter, Math, TimeFreq, Convolve
from ..graphoelement import Spindles

TRIAL = 0
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
    def __init__(self, frequency=(11, 18),
                 method='hilbert', method_options={},
                 threshold='relative', threshold_options={},
                 criteria={}):

        self.frequency = frequency

        self.method = method

        if method == 'wavelet':

            # default options for wavelets
            if 'detect_wavelet' not in method_options:
                method_options['detect_wavelet'] = {}
            method_options['detect_wavelet'].update({'M_in_s': 1,
                                                     'w': 7,
                                                     })

            if 'detect_smoothing' not in method_options:
                method_options['detect_smoothing'] = {}
            method_options['detect_smoothing'].update({'window': 'boxcar',
                                                       'length': 1,
                                                       })

            if 'select_wavelet' not in method_options:
                method_options['select_wavelet'] = None

            if 'select_smoothing' not in method_options:
                method_options['select_smoothing'] = None
        self.method_options = method_options

        self.threshold = threshold
        self.threshold_options = threshold_options

        if 'peak_in_fft' in criteria:
            if 'dryrun' not in criteria['peak_in_fft']:
                criteria['peak_in_fft']['dryrun'] = False
        self.criteria = criteria

    def __call__(self, data):
        """Detect spindles on the data.

        Parameters
        ----------
        data : instance of Data
            data used for detection

        Returns
        -------
        instance of graphoelement.Spindles
            description of the detected spindles

        Notes
        -----
        TODO: multiple trials.

        TODO: sharper wavelets for selection

        """
        if self.method == 'hilbert':
            apply_filter = Filter(low_cut=self.frequency[0],
                                  high_cut=self.frequency[1],
                                  s_freq=data.s_freq)
            filtered = apply_filter(data)

            apply_abs_hilb = Math(operator_name=('hilbert', 'abs'),
                                  axis='time')
            detection_data = apply_abs_hilb(filtered)
            selection_data = detection_data

        elif self.method == 'wavelet':
            calc_tf = TimeFreq(method='morlet',
                              options=self.method_options['detect_wavelet'],
                              foi=arange(self.frequency[0],
                                         self.frequency[1]))
            apply_abs_mean = Math(operator_name=('abs', 'mean'), axis='freq')
            apply_smooth = Convolve(s_freq=data.s_freq,
                                    **self.method_options['detect_smoothing'])

            filtered = apply_smooth(apply_abs_mean(calc_tf(data)))
            selection_data = detection_data = filtered

        time_axis = data.axis['time'][TRIAL]

        if self.threshold == 'relative':
            get_mean = Math(operator_name='mean', axis='time')
            get_std = Math(operator_name='std', axis='time')

            envelope_mean = get_mean(filtered)

            if self.method == 'hilbert':
                envelope_std = get_std(filtered)

                detection_value = (envelope_mean(trial=TRIAL) +
                                   envelope_std(trial=TRIAL) *
                                   self.threshold_options['detection_value'])
                selection_value = (envelope_mean(trial=TRIAL) +
                                   envelope_std(trial=TRIAL) *
                                   self.threshold_options['selection_value'])

            elif self.method == 'wavelet':
                # wavelet signal is always positive
                detection_value = (envelope_mean(trial=TRIAL) *
                                   self.threshold_options['detection_value'])
                selection_value = (envelope_mean(trial=TRIAL) *
                                   self.threshold_options['selection_value'])

        elif self.threshold == 'absolute':
            n_chan = detection_data.number_of('chan')[TRIAL]
            detection_value = (ones(n_chan) *
                               self.threshold_options['detection_value'])
            selection_value = (ones(n_chan) *
                               self.threshold_options['selection_value'])

        all_spindles = []
        if self.threshold in ('relative', 'absolute'):
            for i, chan in enumerate(detection_data.axis['chan'][TRIAL]):

                # 1. detect above threshold
                det_dat = detection_data(trial=TRIAL, chan=chan)
                above_det = det_dat >= detection_value[i]
                detected = _detect_start_end(above_det)

                if detected is None:
                    continue

                # 2. select spindles, based on selection_data
                sel_dat = selection_data(trial=TRIAL, chan=chan)
                above_sel = sel_dat >= selection_value[i]
                detected = _select_complete_period(detected, above_sel)

                # convert to real time
                detected_in_s = time_axis[detected]

                for time_in_smp, time_in_s in zip(detected, detected_in_s):

                    # detect max value in the spindle interval
                    spindle_dat = det_dat[time_in_smp[0]:time_in_smp[1]]
                    peak_smp = spindle_dat.argmax() + time_in_smp[0]

                    one_spindle = {'start_time': time_in_s[0],
                                   'end_time': time_in_s[1],
                                   'peak_time': time_axis[peak_smp],
                                   'peak_val': spindle_dat.max(),
                                   'area_under_curve': sum(spindle_dat),
                                   'chan': chan,
                                   }
                    all_spindles.append(one_spindle)


        elif self.threshold == 'maxima':
            for i, chan in enumerate(detection_data.axis['chan'][TRIAL]):
                order = self.threshold_options['peak_width'] * data.s_freq
                dat = detection_data(trial=TRIAL, chan=chan)
                peaks = argrelmax(dat, order=round(order))[0]
                lg.debug('Found {} peaks'.format(len(peaks)))

                for one_peak in peaks:
                    width = (self.threshold_options['select_width'] *
                             data.s_freq)

                    # search minimum before the peak
                    beg_valley = one_peak - width
                    if beg_valley < 0:
                        continue
                    sp_start = argmin(dat[beg_valley:one_peak]) + beg_valley

                    # search minimum after the peak
                    end_valley = one_peak + width
                    if end_valley > len(dat):
                        continue
                    sp_end = argmin(dat[one_peak:end_valley]) + one_peak

                    spindle_dat = dat[sp_start:sp_end]

                    one_spindle = {'start_time': time_axis[sp_start],
                                   'end_time': time_axis[sp_end],
                                   'peak_time': time_axis[one_peak],
                                   'peak_val': dat[one_peak],
                                   'area_under_curve': sum(spindle_dat),
                                   'chan': chan,
                                   }
                    all_spindles.append(one_spindle)


        lg.info('Number of potential spindles {0}'.format(len(all_spindles)))

        # 3. apply additional criteria
        if 'duration' in self.criteria:
            min_duration = self.criteria['duration'][0]
            max_duration = self.criteria['duration'][1]

            accepted_spindles = []
            for sp in all_spindles:
                sp_dur = sp['end_time'] - sp['start_time']
                if sp_dur >= min_duration and sp_dur <= max_duration:
                    lg.debug('accepting duration ' + str(sp_dur))
                    accepted_spindles.append(sp)
                else:
                    lg.debug('Spindle rejected, duration (s) ' + str(sp_dur))
            all_spindles = accepted_spindles

        if 'peak_in_fft' in self.criteria:
            dryrun = self.criteria['peak_in_fft']['dryrun']

            accepted_spindles = []
            for sp in all_spindles:
                fft_window_length = self.criteria['peak_in_fft']['length']
                peak_freq = _find_peak_in_fft(data, sp['peak_time'],
                                              sp['chan'], fft_window_length)
                if (dryrun or (peak_freq is not None and
                               peak_freq >= self.frequency[0] and
                               peak_freq <= self.frequency[1])):
                    sp['peak_freq'] = peak_freq
                    accepted_spindles.append(sp)
                    lg.debug('Spindle accepted, freq peak (Hz) ' +
                             str(peak_freq))
                else:
                    lg.debug('Spindle rejected, freq peak (Hz) ' +
                             str(peak_freq))
            all_spindles = accepted_spindles


        lg.info('Number of final spindles {0}'.format(len(all_spindles)))

        spindle = Spindles()
        spindle.spindle = all_spindles

        return spindle

    def __str__(self):
        """Prepare string if you want to summarize object to string/file."""
        if self.threshold in ('absolute', 'relative'):
            thr_opt = ('{0:04.1f}-{1:04.1f}'
                       ''.format(self.detection_value, self.selection_value))
        elif self.threshold in ('maxima', ):
            thr_opt = ('{0:04.1f}-{1:04.1f}'
                       ''.format(self.threshold_options['peak_width'],
                                 self.threshold_options['select_width']))

        criteria = []
        if 'duration' in self.criteria:
            criteria.append('dur{0:03.1f}-{1:03.1f}'
                            ''.format(self.criteria['duration'][0],
                                      self.criteria['duration'][1]))
        if 'peak_in_fft' in self.criteria:
            criteria.append('fft{0:04.1f}'
                            ''.format(self.criteria['peak_in_fft']['length']))
        criteria = '_'.join(criteria)

        _str = ('DetectSpindle_{0:04.1f}-{1:04.1f}_{2}_{3}_{4}_{5}'
                ''.format(self.frequency[0], self.frequency[1], self.method,
                          self.threshold, thr_opt, criteria))
        return _str


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


def _select_complete_period(detected, true_values):
    """For the detected values, we check when it goes below the selection.

    Parameters
    ----------
    detected : ndarray (dtype='int')
        2 x N matrix with starting and ending times.
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
        end_sel = where(true_values[one_spindle[0]:])[0]
        if end_sel.any():
            one_spindle[1] += end_sel[0]

    return detected


def _find_peak_in_fft(data, peak_in_s, chan, fft_window_length):
    """Find the peak in the power spectrum.

    Parameters
    ----------
    data : instance of phypno.ChanTime
        the data of interest
    peak_in_s : float
        peak, in seconds, of the spindle
    chan : str
        in which channel the spindle was observed
    fft_window_length : float
        length, in s, of the window used to estimate power spectrum

    Returns
    -------
    float
        value, in Hz, of the peak in power spectrum

    """
    peak_in_smp = _find_nearest(data.axis['time'][TRIAL], peak_in_s)

    beg_fft = peak_in_smp - data.s_freq * fft_window_length / 2
    end_fft = peak_in_smp + data.s_freq * fft_window_length / 2

    if beg_fft < 0 or end_fft > data.number_of('time')[TRIAL]:
        return None

    time_for_fft = data.axis['time'][0][beg_fft:end_fft]

    x = data(trial=TRIAL, chan=chan, time=time_for_fft)
    f, Pxx = welch(x, data.s_freq, nperseg=data.s_freq)

    idx_peak = Pxx[f < MAX_FREQUENCY_OF_INTEREST].argmax()
    return f[idx_peak]


def _find_nearest(array, value):
    """Find nearest value in one array.

    Parameters
    ----------
    array : ndarray
        vector with values
    value : value of interest

    Returns
    -------
    int
        index of the array value closest to value of interest.

    """
    return abs(array - value).argmin()
