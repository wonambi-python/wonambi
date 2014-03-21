"""Module contains the different types of data formats.

The main class is Data, all the other classes should depend on it. The other
classes are given only as convenience, but they should not overwride
Data.__call__, which needs to be very general

Notes
-----
There is a circular import (we use Select, which depends on datatype)

TODO: probably it's best to return the number of chan, freq, time. If None, it
means that the dimension does not exist.

use something like this to slice any dimension:

s[axis] = slice(1, n)
C = A[s]

XXX don't use intervals here, you can only use those in Select. Here you need
to pass the actual values.

XXX this should be views (can be modified), Select should deep-copy

"""
from collections import OrderedDict
from logging import getLogger
from numpy import absolute, array, empty, in1d, min, zeros


lg = getLogger('phypno')


def _select_arbitrary_dimensions(n_dim, axis, idx):
    """Select along a specified dimension.

    Parameters
    ----------
    n_dim : int
        number of dimensions in the original data
    axis : int
        index of the axis along which the selection occurs.
    idx : list/tuple of int or ndarray(dtype='int')
        indices of the elements to select.

    Returns
    -------
    list of slice
        slice along one dimension.

    Notes
    -----
    It's a pretty neat code to select along an arbitrary axis. You can only
    select one dimension at the time.

    """
    selection = [slice(None), ] * n_dim
    selection[axis] = idx

    return selection


def _get_indices(values, selected, tolerance):
    """Get indices based on user-selected values.

    Parameters
    ----------
    values : ndarray (any dtype)
        values present in the dimension.
    selected : ndarray (any dtype) or tuple or list
        values selected by the user
    tolerance : float
        avoid rounding errors.

    Returns
    -------
    ndarray (dtype='bool')
        boolean values to select or not select values.

    Notes
    -----
    If you use values in the dimension, you don't need to specify tolerance.
    However, if you specify arbitrary points, floating point errors might
    affect the actual values. Of course, using tolerance is much slower.

    Maybe tolerance should be part of Select instead of here.

    """
    if tolerance is None or values.dtype.kind == 'U':
        idx = in1d(values, selected)
    else:
        idx = zeros(len(values), dtype='bool')
        for i, one_value in enumerate(values):
            idx[i] = min(absolute(one_value - selected)) <= tolerance

    return idx


class Data:
    """General class containing recordings.

    Attributes
    ----------
    data : ndarray (dtype='O')
        the data as trials. Each trial is a ndarray (dtype='d' or 'f')
    dim : OrderedDict
        dictionary with dimensions (standard names are 'chan', 'time', 'freq')
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
        self.dim = OrderedDict()
        self.start_time = None
        self.s_freq = None
        self.attr = {'surf': None,
                     'chan': None,
                     'scores': None,
                     }

    def __call__(self, trial=None, tolerance=None, **dimensions):
        """Return the recordings and their time stamps.

        Parameters
        ----------
        trial : list of int or ndarray (dtype='i') or int
            which trials you want (if it's one int, it returns the actual
            matrix)

        chan : list of str
            which channels you want
        time : tuple of 2 float
            which periods you want. If one of the tuple is None, keep it.

        Returns
        -------
        data : ndarray (dtype='O')
            ndarray containing chan X time matrix of the recordings

        Notes
        -----
        I wish it returned a view of the data, but actually it probably copies
        it anyway. It might not be that bad after all.

        i is always the index over trials.

        """
        if trial is None:
            trial = range(self.number_of('trial'))

        squeeze = False
        try:
            iter(trial)
        except TypeError:  # 'int' object is not iterable
            trial = (trial, )
            squeeze = True

        output = empty(len(trial), dtype='O')

        for cnt, i in enumerate(trial):
            output[cnt] = self.data[i]
            for dim, user_idx in dimensions.items():

                axis = self.index_of(dim)
                idx = _get_indices(self.dim[dim][i], user_idx,
                                   tolerance=tolerance)
                if not any(idx):
                    lg.warning('No index was selected for ' + dim)
                sel = _select_arbitrary_dimensions(len(self.dim),
                                                   axis, idx)
                output[cnt] = output[cnt][sel]

        if squeeze:
            output = output[0]

        return output

    def index_of(self, dim):
        """Return the index of a dimension.

        Parameters
        ----------
        dim : str
            Name of the dimension (such as 'trial', 'time', etc)

        Returns
        -------
        int or ndarray (dtype='int')
            number of trial (as int) or number of element in the selected
            dimension (if any of the other dimensions) as 1d array.

        Raises
        ------
        ValueError
            If the requested dimension is not in the data.

        """
        return list(self.dim.keys()).index(dim)

    def number_of(self, dim):
        """Return the number of in one dimension, as generally as possible.

        Parameters
        ----------
        dim : str
            Name of the dimension (such as 'trial', 'time', etc)

        Returns
        -------
        int or ndarray (dtype='int')
            number of trial (as int) or number of element in the selected
            dimension (if any of the other dimensions) as 1d array.

        Raises
        ------
        KeyError
            If the requested dimension is not in the data.

        Notes
        -----
        or is it better to catch the exception?

        """
        if dim == 'trial':
            return len(self.data)
        else:
            n_trial = self.number_of('trial')
            output = empty(n_trial, dtype='int')
            for i in range(n_trial):
                output[i] = len(self.dim[dim][i])

            return output


class ChanTime(Data):
    """Specific class for chan-time recordings.

    Dimensions
    ----------
    chan : ndarray (dtype='O')
        which channels you want
    time : ndarray (dtype='O')
        the time in trials. Each trial is a 1d ndarray (dtype='d' or 'f')

    """
    def __init__(self):
        super().__init__()
        self.dim['chan'] = array([], dtype='O')
        self.dim['time'] = array([], dtype='O')


class ChanFreq(Data):
    """Specific class for channel-frequency recordings.

    Dimensions
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
        self.dim['chan'] = array([], dtype='O')
        self.dim['freq'] = array([], dtype='O')


class ChanTimeFreq(Data):
    """Specific class for channel-time-frequency representation.

    Dimensions
    ----------
    chan

    time : numpy.ndarray
        1d matrix with the time stamp
    freq : numpy.ndarray
        1d matrix with the frequency

    """
    def __init__(self):
        super().__init__()
        self.dim['chan'] = array([], dtype='O')
        self.dim['time'] = array([], dtype='O')
        self.dim['freq'] = array([], dtype='O')
