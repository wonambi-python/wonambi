from numpy import nan, nanargmax, nanargmin
from copy import deepcopy


class Peaks:
    """Return the values of an index where the data is at max or min

    Parameters
    ----------
    method : str, optional
        'max' or 'min'
    axis : str, optional
        the axis where you want to detect the peaks
    limits : tuple of two values, optional
        the lowest and highest limits where to search for the peaks

    Notes
    -----
    This function is useful when you want to find the frequency value at which
    the power is the largest, or to find the time point at which the signal is
    largest, or the channel at which the activity is largest.

    """
    def __init__(self, method='max', axis='time', limits=None):

        self.method = method
        self.axis = axis
        self.limits = limits

    def __call__(self, data):
        """Calculate peaks on the data.

        Parameters
        ----------
        data : instance of Data
            one of the datatypes

        Returns
        -------
        instance of Data
            with one dimension less that the input data. The actual values in
            the data can be not-numberic, for example, if you look for the
            max value across electrodes

        """
        idx_axis = data.index_of(self.axis)
        output = deepcopy(data)
        output.axis.pop(self.axis)

        for trl in range(data.number_of('trial')):
            values = data.axis[self.axis][trl]
            dat = data(trial=trl)

            if self.limits is not None:
                limits = (values < self.limits[0]) | (values > self.limits[1])

                idx = [slice(None)] * len(data.list_of_axes)
                idx[idx_axis] = limits
                dat[idx] = nan

            if self.method == 'max':
                peak_val = nanargmax(dat, axis=idx_axis)
            elif self.method == 'min':
                peak_val = nanargmin(dat, axis=idx_axis)

            output.data[trl] = values[peak_val]

        return output
