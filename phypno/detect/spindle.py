"""Module to detect spindles.

"""
from logging import getLogger
lg = getLogger('phypno')

from collections import Iterable

from numpy import (asarray, diff, hstack, invert, ones, squeeze, vstack,
                   where, zeros)

from ..graphoelement import Spindles


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

    Returns
    -------
    instance of Spindles
        description of the detected spindles

    Notes
    -----
    If you pass 'threshold_type' as 'absolute', you should pass only one value
    for all the channels. If you use 'relative', you should pass one value
    per channel. Note that the values are always in absolute units, if you want
    to use median + standard deviation, you need to do it outside of this
    function.

    Merging of the spindles will occur somewhere else.

    """
    def __init__(self, threshold_type='absolute', detection_threshold=None,
                 selection_threshold=None,
                 minimal_duration=0.5, maximal_duration=2):

        if threshold_type == 'absolute':
            if isinstance(detection_threshold, Iterable):
                raise TypeError('If threshold is absolute, detection_threshold'
                                ' should be a single value')
            if (selection_threshold is not None and
                isinstance(selection_threshold, Iterable)):
                raise TypeError('If threshold is absolute, selection_threshold'
                                ' should be a single value')

        if threshold_type == 'relative':
            if not isinstance(detection_threshold, Iterable):
                raise TypeError('If threshold is relative, detection_threshold'
                                ' should be a vector')
            if (selection_threshold is not None and
                not isinstance(selection_threshold, Iterable)):
                raise TypeError('If threshold is relative, selection_threshold'
                                ' should be a vector')

        self.threshold_type = threshold_type
        self.detection_threshold = detection_threshold
        self.selection_threshold = selection_threshold
        self.minimal_duration = minimal_duration
        self.maximal_duration = maximal_duration


    def __call__(self, detection_data, selection_data=None):
        """Detect spindles on the data.

        Parameters
        ----------
        detection_data : instance of Data
            data used for detection

        selection_data : instance of Data, optional
            data used for selection. If empty, detection_data will be used.


        Notes
        -----
        TODO: multiple trials.
        """
        if selection_data is None:
            selection_data = detection_data

        if self.threshold_type == 'absolute':
            n_chan = detection_data.number_of('chan')
            self.detection_threshold = (ones(n_chan) *
                                        self.detection_threshold)
            self.selection_threshold = (ones(n_chan) *
                                        self.selection_threshold)

        all_spindles = []

        for i, chan in enumerate(detection_data.axis['chan'][0]):
            lg.info('Reading chan #' + chan)

            detected = _detect_spindles(detection_data(trial=0, chan=chan),
                                        self.detection_threshold[i],
                                        selection_data(trial=0, chan=chan),
                                        self.selection_threshold[i],
                                        detection_data.axis['time'][0])

            if detected is None:
                lg.info('No spindles were detected')
                continue

            lg.info('Detected ' + str(detected.shape[0]) +
                    ' spindles')

            for one_detected in detected:
                one_spindle = {'start_time': one_detected[0],
                               'end_time': one_detected[1],
                               'chan': chan,
                               }

                all_spindles.append(one_spindle)

        spindle = Spindles()
        spindle.spindle = all_spindles

        return spindle


def _detect_spindles(detection_data, detection_value,
                     selection_data, selection_value,
                     time_axis, minimal_duration, maximal_duration):
        """Function doing the actual detection.

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

        """
        # 1. detect spindles, based on detection_data
        above_det = detection_data >= detection_value
        detected = _detect_start_end(above_det)

        if detected is None:
            return None

        lg.debug('Potential spindles: ' + str(detected.shape[1]))

        # 2. select spindles, based on selection_data
        above_sel = selection_data >= selection_value
        detected = _select_complete_period(detected, above_sel)

        # convert to real time
        detected_in_s = time_axis[detected]

        # 3. apply additional criteria
        duration = squeeze(diff(detected_in_s), axis=1)
        good_duration = ((duration >= minimal_duration) &
                         (duration <= maximal_duration))

        return detected_in_s[good_duration, :]


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
