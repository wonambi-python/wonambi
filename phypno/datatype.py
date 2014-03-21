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

A = np.random.rand(2, 3, 4, 5)
axis = 2
n = A.ndim
# building n-dimensional slice
s = [slice(None), ] * n
s[axis] = slice(0, n - 1)
B = A[s]
s[axis] = slice(1, n)
C = A[s]



XXX this should be views (can be modified), Select should deep-copy

"""
from collections import OrderedDict
from logging import getLogger
from numpy import array

lg = getLogger('phypno')


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

    def __call__(self, trial=None, **dimensions):
        """Return the recordings and their time stamps.

        Parameters
        ----------
        trial : list of int or ndarray (dtype='i')
            which trials you want
        chan : list of str
            which channels you want
        time : tuple of 2 float
            which periods you want. If one of the tuple is None, keep it.

        Returns
        -------
        data : ndarray (dtype='O')
            ndarray containing chan X time matrix of the recordings

        """

        # TODO: Always data, and then the dimensions (in order)

        return self

    def number_of(self, dim):
        """Return the number of in one dimension, as generally as possible.

        Parameters
        ----------
        dim : str
            Name of the dimension (such as 'trial', 'time', etc)

        Returns
        -------
        int
            number of elements in one dimension.

        """
        if dim == 'trial':
            return len(self.data)
        else:
            try:
                return len(self.dim[dim])
            except KeyError:
                return None


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
