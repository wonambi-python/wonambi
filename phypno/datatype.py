"""Module contains the different types of data formats.

The main class is Data, all the other classes should depend on it. The other
classes are given only as convenience, but they should not overwride
Data.__call__, which needs to be very general.

"""
from collections import OrderedDict
from logging import getLogger
from numpy import arange, array, empty, ix_, NaN, ndarray, squeeze, where


lg = getLogger('phypno')


def _get_indices(values, selected, tolerance):
    """Get indices based on user-selected values.

    Parameters
    ----------
    values : ndarray (any dtype)
        values present in the axis.
    selected : ndarray (any dtype) or tuple or list
        values selected by the user
    tolerance : float
        avoid rounding errors.

    Returns
    -------
    idx_data : list of int
        indices of row/column to select the data
    idx_output : list of int
        indices of row/column to copy into output

    Notes
    -----
    This function is probably not very fast, but it's pretty robust. It keeps
    the order, which is extremely important.

    If you use values in the self.axis, you don't need to specify tolerance.
    However, if you specify arbitrary points, floating point errors might
    affect the actual values. Of course, using tolerance is much slower.

    Maybe tolerance should be part of Select instead of here.

    """
    idx_data = []
    idx_output = []
    for idx_of_selected, one_selected in enumerate(selected):

        if tolerance is None or values.dtype.kind == 'U':
            idx_of_data = where(values == one_selected)[0]
        else:
            idx_of_data = where(abs(values - one_selected) <= tolerance)[0] # actual use min

        if len(idx_of_data) > 0:
            idx_data.append(idx_of_data[0])
            idx_output.append(idx_of_selected)

    return idx_data, idx_output


class Data:
    """General class containing recordings.

    Attributes
    ----------
    data : ndarray (dtype='O')
        the data as trials. Each trial is a ndarray (dtype='d' or 'f')
    axis : OrderedDict
        dictionary with axiss (standard names are 'chan', 'time', 'freq')
    start_time : instance of datetime.datetime
        the start time of the recording
    attr : dict
        contains additional information about the dataset, with keys:
            - surf
            - chan
            - scores

    Notes
    -----
    Something which is not immediately clear for chan. dtype='U' (meaning
    Unicode) actually creates string of type 'str_', while if you use dtype='S'
    (meaning String) it creates strings of type 'bytes_'.

    """
    def __init__(self):
        self.data = array([], dtype='O')
        self.axis = OrderedDict()
        self.start_time = None
        self.s_freq = None
        self.attr = {'surf': None,
                     'chan': None,
                     'scores': None,
                     }

    def __call__(self, trial=None, tolerance=None, **axes):
        """Return the recordings and their time stamps.

        Parameters
        ----------
        trial : list of int or ndarray (dtype='i') or int
            which trials you want (if it's one int, it returns the actual
            matrix).
        **axes
            Arbitrary axiss to select from. You specify the axis and
            the values as list or tuple of the values that you want.
        tolerance : float
            if one of the axiss is a number, it specifies the tolerance to
            consider one value as chosen (take into account floating-precision
            errors).

        Returns
        -------
        ndarray
            ndarray containing the data with the same number of axiss as
            the original data. The length of the axis is equal to the
            length of the data, UNLESS you specify an axis with values. In
            that case, the length is equal to the values that you want.

            If you specify only one trial (as int, not as tuple or list), then
            it returns the actual matrix. Otherwise, it returns a ndarray
            (dtype='O') of length equal to the trials.

        Notes
        -----
        You cannot specify intervals here, you can do it in Select.

        XXX: squeeze any dimension, if the user specifies only one value

        """
        if trial is None:
            trial = range(self.number_of('trial'))

        squeeze_trial = False
        try:
            iter(trial)
        except TypeError:  # 'int' object is not iterable
            trial = (trial, )
            squeeze_trial = True

        output = empty(len(trial), dtype='O')

        for cnt, i in enumerate(trial):

            output_shape = []
            idx_data = []
            idx_output = []
            squeeze_axis = []

            for axis, values in self.axis.items():
                if axis in axes.keys():
                    selected_values = axes[axis]
                    if not isinstance(selected_values, str):
                        n_values = len(selected_values)
                    elif isinstance(selected_values, ndarray):
                        n_values = selected_values.shape[0]
                    else:
                        n_values = 1
                        selected_values = (selected_values, )
                        squeeze_axis.append(self.index_of(axis))

                    idx = _get_indices(values[i],
                                       selected_values,
                                       tolerance=tolerance)
                    if len(idx[0]) == 0:
                        lg.warning('No index was selected for ' + axis)

                    idx_data.append(idx[0])
                    idx_output.append(idx[1])
                else:
                    n_values = len(values[i])
                    idx_data.append(arange(n_values))
                    idx_output.append(arange(n_values))

                output_shape.append(n_values)

            output[cnt] = empty(output_shape, dtype=self.data[i].dtype)
            output[cnt][:] = NaN

            if all([len(x) > 0 for x in idx_data]):
                ix_output = ix_(*idx_output)
                ix_data = ix_(*idx_data)
                output[cnt][ix_output] = self.data[i][ix_data]

                if len(squeeze_axis) > 0:
                    output[cnt] = squeeze(output[cnt],
                                          axis=tuple(squeeze_axis))

        if squeeze_trial:
            output = output[0]

        return output

    def index_of(self, axis):
        """Return the index of a axis.

        Parameters
        ----------
        axis : str
            Name of the axis (such as 'trial', 'time', etc)

        Returns
        -------
        int or ndarray (dtype='int')
            number of trial (as int) or number of element in the selected
            axis (if any of the other axiss) as 1d array.

        Raises
        ------
        ValueError
            If the requested axis is not in the data.

        """
        return list(self.axis.keys()).index(axis)

    def number_of(self, axis):
        """Return the number of in one axis, as generally as possible.

        Parameters
        ----------
        axis : str
            Name of the axis (such as 'trial', 'time', etc)

        Returns
        -------
        int or ndarray (dtype='int')
            number of trial (as int) or number of element in the selected
            axis (if any of the other axiss) as 1d array.

        Raises
        ------
        KeyError
            If the requested axis is not in the data.

        Notes
        -----
        or is it better to catch the exception?

        """
        if axis == 'trial':
            return len(self.data)
        else:
            n_trial = self.number_of('trial')
            output = empty(n_trial, dtype='int')
            for i in range(n_trial):
                output[i] = len(self.axis[axis][i])

            return output


class ChanTime(Data):
    """Specific class for chan-time recordings.

    axiss
    ----------
    chan : ndarray (dtype='O')
        which channels you want
    time : ndarray (dtype='O')
        the time in trials. Each trial is a 1d ndarray (dtype='d' or 'f')

    """
    def __init__(self):
        super().__init__()
        self.axis['chan'] = array([], dtype='O')
        self.axis['time'] = array([], dtype='O')


class ChanFreq(Data):
    """Specific class for channel-frequency recordings.

    axiss
    ----------
    freq : ndarray (dtype='O')
        the freq in trials. Each trial is a 1d ndarray (dtype='d' or 'f')

    Notes
    -----
    Conceptually, it is reasonable that each trial has the same frequency band,
    so it might be more convenient to use only one array, but it can happen
    that different trials have different frequency bands, so we keep the format
    more open.

    """
    def __init__(self):
        super().__init__()
        self.axis['chan'] = array([], dtype='O')
        self.axis['freq'] = array([], dtype='O')


class ChanTimeFreq(Data):
    """Specific class for channel-time-frequency representation.

    axiss
    ----------
    chan

    time : numpy.ndarray
        1d matrix with the time stamp
    freq : numpy.ndarray
        1d matrix with the frequency

    """
    def __init__(self):
        super().__init__()
        self.axis['chan'] = array([], dtype='O')
        self.axis['time'] = array([], dtype='O')
        self.axis['freq'] = array([], dtype='O')
