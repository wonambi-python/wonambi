from logging import getLogger
from numpy import nan, nanargmax, nanargmin

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
