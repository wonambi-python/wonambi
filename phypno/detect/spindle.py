"""Module to detect spindles.

"""
from logging import getLogger
lg = getLogger('phypno')

from collections import Iterable

from numpy import (asarray, diff, hstack, invert, ones, vstack, where, zeros)

from ..trans import Filter, Math
from ..graphoelement import Spindles

TRIAL = 0


class DetectSpindle:
    """Design spindle detection on a single channel.

    Parameters
    ----------
    threshold_type : str
        typeof threshold ('absolute', 'relative')
    detection_threshold : float or ndarray (dtype='f')
        the value used for the threhsold
    selection_threshold : float or ndarray (dtype='f')
        the value used to calculate the start and end of the spindle
    minimal_duration : float
        minimal duration in s to be considered a spindle
    maximal_duration : float
        maximal duration in s to be considered a spindle

        Parameters
        ----------
        detection_data : ndarray
            1d matrix with data for one channel used for selection
        detection_value : float
            threshold for detection for this channel
        selection_data : ndarray
            1d matrix with data for one channel used for selection
        selection_value : float
            threshold for detection for this channel
        time_axis: ndarray
            time points for each data point
        minimal_duration : float
            minimal duration of spindle in s
        maximal_duration : float
            maximal duration of spindle in s

        Returns
        -------
        ndarray
            2d array, first column starting time of each spindle and second
            column the end time.


    Returns
    -------
    instance of Spindles
        description of the detected spindles

    """
    def __init__(self, method='hilbert', frequency=(11, 20),
                 threshold_type='absolute',
                 detection_threshold=None, selection_threshold=None,
                 duration=(0.5, 2)):

        self.method = 'hilbert'
        self.frequency = frequency
        self.threshold_type = threshold_type
        self.detection_threshold = detection_threshold
        self.selection_threshold = selection_threshold
        self.duration = duration

    def __call__(self, data):
        """Detect spindles on the data.

        Parameters
        ----------
        data : instance of Data
            data used for detection

        Notes
        -----
        TODO: multiple trials.

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

        if self.threshold_type == 'relative':
            get_mean = Math(operator_name='mean', axis='time')
            get_std = Math(operator_name='std', axis='time')

            envelope_mean = get_mean(filtered)
            envelope_std = get_std(filtered)

            detection_threshold = (envelope_mean(trial=0) +
                                   envelope_std(trial=0) *
                                   self.detection_threshold)
            selection_threshold = (envelope_mean(trial=0) +
                                   envelope_std(trial=0) *
                                   self.selection_threshold)

        elif self.threshold_type == 'absolute':
            n_chan = detection_data.number_of('chan')
            detection_threshold = (ones(n_chan) * self.detection_threshold)
            selection_threshold = (ones(n_chan) * self.selection_threshold)

        all_spindles = []
        if self.threshold_type in ('relative', 'absolute'):
            for i, chan in enumerate(detection_data.axis['chan'][TRIAL]):

                # 1. detect above threshold
                det_dat = detection_data(trial=TRIAL, chan=chan)
                above_det = det_dat >= detection_threshold[i]
                detected = _detect_start_end(above_det)

                if detected is None:
                    continue

                # 2. select spindles, based on selection_data
                sel_dat = selection_data(trial=TRIAL, chan=chan)
                above_sel = sel_dat >= selection_threshold[i]
                detected = _select_complete_period(detected, above_sel)

                # convert to real time
                time_axis = data.axis['time'][TRIAL]
                detected_in_s = time_axis[detected]

                for time_in_smp, time_in_s in zip(detected, detected_in_s):
                    one_spindle = {'start_time': time_in_s[0],
                                   'end_time': time_in_s[1],
                                   'start_sample': time_in_smp[0],
                                   'end_sample': time_in_smp[1],
                                   'chan': chan,
                                   }
                    all_spindles.append(one_spindle)

        lg.info('Number of potential spindles {0}'.format(len(all_spindles)))

        # 3. apply additional criteria
        if self.duration is not None:
            for sp in all_spindles:
                sp_dur = sp['end_time'] - sp['start_time']
                if not (self.duration[0] <= sp_dur <= self.duration[1]):
                    all_spindles.remove(sp)

        lg.info('Number of final spindles {0}'.format(len(all_spindles)))

        spindle = Spindles()
        spindle.spindle = all_spindles

        return spindle


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
