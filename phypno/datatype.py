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
from logging import getLogger
from numpy import array, squeeze, asarray, hstack
lg = getLogger('phypno')


class Data:
    """General class containing recordings.

    Attributes
    ----------
    data : ndarray (dtype='O')
        the data as trials. Each trial is a ndarray (dtype='d' or 'f')
    chan_name : ndarray (dtype='U')
        labels of the channels
    start_time : instance of datetime.datetime
        the start time of the recording
    attr : dict
        contains additional information about the dataset, with keys:
            - surf
            - chan
            - scores

    Notes
    -----
    Something which is not immediately clear for chan_name. dtype='U' (meaning
    Unicode) actually creates string of type 'str_', while if you use dtype='S'
    (meaning String) it creates strings of type 'bytes_'.

    """
    def __init__(self):
        self.data = array([], dtype='O')
        self.chan_name = array([], dtype='U')
        self.start_time = None
        self.s_freq = None
        self.attr = {'surf': None,  # TODO: instance of class surf
                     'chan': None,  # TODO: instance of class chan
                     'scores': None,
                     }


class DataTime(Data):
    """Specific class for time-voltage recordings.

    Attributes
    ----------
    time : ndarray, dtype='O'
        the time in trials. Each trial is a 1d ndarray, dtype='d' (or 'f')

    """
    def __init__(self):
        super().__init__()
        self.time = array([], dtype='O')

    def __call__(self, trial=None, chan=None, time=None):
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
        time : ndarray (dtype='O')
            ndarray containing 1d matrix with the time stamp

        """
        from .trans.select import Select
        selection = Select(chan=chan, time=time)
        output = selection(self)

        return output.data, output.time


class DataFreq(Data):
    """Specific class for frequency-power recordings.

    Attributes
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
        self.freq = array([], dtype='O')

    def __call__(self, trial=None, chan=None, freq=None):
        """Return the power spectrum and their frequency indices.

        Parameters
        ----------
        chan : list of str
            which channels you want
        freq : tuple of 2 float
            which frequency you want. If one of the tuple is None, keep it.

        Returns
        -------
        data : ndarray (dtype='O')
            ndarray containing chan X freq matrix of the power spectrum
        freq : ndarray (dtype='O')
            ndarray containing 1d matrix with the frequency

        Notes
        -----
        Internally, each trial in .data is stored as a 3d matrix, with
        chan X time X freq, but time is always one dimension. When you call the
        function directly, it returns a 2d matrix, with chan X freq, where time
        doesn't exist.

        """
        from .trans.select import Select
        selection = Select(chan=chan, freq=freq)
        output = selection(self)

        for i in range(len(output.data)):
            output.data[i] = squeeze(output.data[i], axis=1)

        return output.data, output.freq


class DataTimeFreq(DataTime, DataFreq):
    """Specific class for time-frequency representation.

    Attributes
    ----------
    time : numpy.ndarray
        1d matrix with the time stamp
    freq : numpy.ndarray
        1d matrix with the frequency

    """
    def __init__(self):
        super().__init__()

    def __call__(self, trial=None, chan=None, time=None, freq=None):
        """Return the power spectrum and their time and frequency indices.

        Parameters
        ----------
        chan : list of str
            which channels you want
        time : tuple of 2 float
            which periods you want. If one of the tuple is None, keep it.
        freq : tuple of 2 float
            which frequency you want. If one of the tuple is None, keep it.

        Returns
        -------
        data : numpy.ndarray
            chan X time X freq matrix of the power spectrum
        time : numpy.ndarray
            1d matrix with the time stamp
        freq : numpy.ndarray
            1d matrix with the frequency

        """
        from .trans.select import Select
        selection = Select(chan=chan, time=time, freq=freq)
        output = selection(self)
        return output.data, output.time, output.freq
