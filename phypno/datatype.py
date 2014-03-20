"""Module contains the different types of data formats.

The main class is Data, all the other classes should depend on it.

Notes
-----
Maybe we could use slice notation (using __getitem__()) instead of call.
I quite like __call__ because it returns a tuple, which is pretty interesting.
But I'm not sure if it's useful.
In addition, the slice notation is not robust enough. The data is a
representation which is only meaningful when including the other parameters,
such as time, freq, chan.
It's always possible to use slice notation on data.data.

With the current implementation, when you call a class in datatype, you get
tuple of matrices. To get a subset of the data, call the functions in the
trans.select module.

There is a circular import (we use Select, which depends on datatype)

"""
from collections import OrderedDict
from logging import getLogger
from numpy import array, squeeze
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
        from .trans.select import Select
        selection = Select(trial=trial, dimensions)
        output = selection(self)

        # TODO: Always data, and then the dimensions that were requested

        return output.data


class DataTime(Data):
    """Specific class for chan-time recordings.

    Dimensions
    ----------
    chan : list of str
        which channels you want
    time : ndarray (dtype='O')
        the time in trials. Each trial is a 1d ndarray (dtype='d' or 'f')

    """
    def __init__(self):
        super().__init__()
        self.dim['chan'] = array([], dtype='0')
        self.dim['time'] = array([], dtype='O')


class DataFreq(Data):
    """Specific class for frequency-power recordings.

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
        self.dim['chan'] = array([], dtype='0')
        self.dim['freq'] = array([], dtype='O')


class DataTimeFreq(Data):
    """Specific class for time-frequency representation.

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
        self.dim['chan'] = array([], dtype='0')
        self.dim['time'] = array([], dtype='O')
        self.dim['freq'] = array([], dtype='O')
