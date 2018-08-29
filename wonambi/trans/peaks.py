from logging import getLogger
from numpy import (asarray, diff, empty, isinf, nan, nanargmax, nanargmin, 
                   negative, ones, sign, where)
from scipy.signal import fftconvolve

lg = getLogger(__name__)


def peaks(data, method='max', axis='time', limits=None):
    """Return the values of an index where the data is at max or min

    Parameters
    ----------
    method : str, optional
        'max' or 'min'
    axis : str, optional
        the axis where you want to detect the peaks
    limits : tuple of two values, optional
        the lowest and highest limits where to search for the peaks
    data : instance of Data
        one of the datatypes

    Returns
    -------
    instance of Data
        with one dimension less that the input data. The actual values in
        the data can be not-numberic, for example, if you look for the
        max value across electrodes

    Notes
    -----
    This function is useful when you want to find the frequency value at which
    the power is the largest, or to find the time point at which the signal is
    largest, or the channel at which the activity is largest.
    """
    idx_axis = data.index_of(axis)
    output = data._copy()
    output.axis.pop(axis)

    for trl in range(data.number_of('trial')):
        values = data.axis[axis][trl]
        dat = data(trial=trl)

        if limits is not None:
            limits = (values < limits[0]) | (values > limits[1])

            idx = [slice(None)] * len(data.list_of_axes)
            idx[idx_axis] = limits
            dat[idx] = nan

        if method == 'max':
            peak_val = nanargmax(dat, axis=idx_axis)
        elif method == 'min':
            peak_val = nanargmin(dat, axis=idx_axis)

        output.data[trl] = values[peak_val]

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
    data = negative(data) # legacy code
    
    nan_array = empty((5,))
    nan_array[:] = nan
    idx_trough = data.argmin()
    idx_peak = data.argmax()
    if idx_trough >= idx_peak:
        return nan_array, nan_array

    zero_crossings_0 = where(diff(sign(data[:idx_trough])))[0]
    zero_crossings_1 = where(diff(sign(data[idx_trough:idx_peak])))[0]
    zero_crossings_2 = where(diff(sign(data[idx_peak:])))[0]
    if zero_crossings_1.any():
        idx_zero_1 = idx_trough + zero_crossings_1[0]
    else:
        return nan_array, nan_array

    if zero_crossings_0.any():
        idx_zero_0 = zero_crossings_0[-1]
    else:
        idx_zero_0 = 0

    if zero_crossings_2.any():
        idx_zero_2 = idx_peak + zero_crossings_2[0]
    else:
        idx_zero_2 = len(data) - 1

    avgsl = nan_array
    if level in ['average', 'all']:
        q1 = data[idx_trough] / ((idx_trough - idx_zero_0) / s_freq)
        q2 = data[idx_trough] / ((idx_zero_1 - idx_trough) / s_freq)
        q3 = data[idx_peak] / ((idx_peak - idx_zero_1) / s_freq)
        q4 = data[idx_peak] / ((idx_zero_2 - idx_peak) / s_freq)
        q23 = (data[idx_peak] - data[idx_trough]) \
                / ((idx_peak - idx_trough) / s_freq)
        avgsl = asarray([q1, q2, q3, q4, q23])
        avgsl[isinf(avgsl)] = nan

    maxsl = nan_array
    if level in ['maximum', 'all']:

        if smooth is not None:
            win = int(smooth * s_freq)
            flat = ones(win)
            data = fftconvolve(data, flat / sum(flat), mode='same')

        if idx_trough - idx_zero_0 >= win:
            maxsl[0] = min(diff(data[idx_zero_0:idx_trough]))

        if idx_zero_1 - idx_trough >= win:
            maxsl[1] = max(diff(data[idx_trough:idx_zero_1]))

        if idx_peak - idx_zero_1 >= win:
            maxsl[2] = max(diff(data[idx_zero_1:idx_peak]))

        if idx_zero_2 - idx_peak >= win:
            maxsl[3] = min(diff(data[idx_peak:idx_zero_2]))

        if idx_peak - idx_trough >= win:
            maxsl[4] = max(diff(data[idx_trough:idx_peak]))

        maxsl[isinf(maxsl)] = nan

    return avgsl, maxsl