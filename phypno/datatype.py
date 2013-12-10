"""Module contains the different types of data formats.

The main class is Data, all the other classes should depend on it.

"""
from numpy import array


class Data:
    """General class containing recordings.

    Attributes
    ----------
    data : numpy.ndarray
        the data, with different number of dimensions
    chan_name : list of str
        labels of the channels
    start_time : instance of datetime.datetime
        the start time of the recording
    attr : dict
        contains additional information about the dataset, with keys:
            - surf
            - chan

    """
    def __init(self):
        self.data = array([])
        self.chan_name = []
        self.start_time = None
        self.attr = {'surf': None,  # TODO: instance of class surf
                     'chan': None,  # TODO: instance of class surf
                     }


class DataRaw(Data):
    """Specific class for time-voltage recordings.

    Attributes
    ----------
    time : numpy.ndarray
        1d matrix with the time stamp

    """
    time = array([])

    def __call__(self):
        """Return the recordings and their time stamps.

        Parameters
        ----------
        TODO: index for channels and time

        Returns
        -------
        data : numpy.ndarray
            time X chan matrix of the recordings
        time : numpy.ndarray
            1d matrix with the time stamp

        """
        return self.data, self.time


class DataFreq(Data):
    """Specific class for frequency-power recordings.

    Attributes
    ----------
    freq : numpy.ndarray
        1d matrix with the frequency

    """
    freq = array([])

    def __call__(self):
        """Return the power spectrum and their frequency indices.

        Parameters
        ----------
        TODO: index for channels and frequency

        Returns
        -------
        data : numpy.ndarray
            time X chan matrix of the power spectrum
        freq : numpy.ndarray
            1d matrix with the frequency

        """
        return self.data, self.freq


class DataTimeFreq(Data):
    """Specific class for time-frequency representation.

    Attributes
    ----------
    time : numpy.ndarray
        1d matrix with the time stamp
    freq : numpy.ndarray
        1d matrix with the frequency

    """
    time = array([])
    freq = array([])

    def __call__(self):
        """Return the power spectrum and their time and frequency indices.

        Parameters
        ----------
        TODO: index for channels, frequency and time

        Returns
        -------
        data : numpy.ndarray
            time X chan matrix of the power spectrum
        time : numpy.ndarray
            1d matrix with the time stamp
        freq : numpy.ndarray
            1d matrix with the frequency

        """
        return self.data, self.time, self.freq
