from datetime import datetime
from logging import getLogger
from numpy import arange
from numpy.random import rand
from ..datatype import DataTime, DataFreq, DataTimeFreq

lg = getLogger('phypno')


def create_data(datatype='DataTime', start_time=None, chan_name=None, n_chan=8,
                s_freq=None, time=None, freq=None):
    """Create data of different datatype from scratch.

    Parameters
    ----------
    datatype : str, optional
        one of 'DataTime', 'DataFreq', 'DataTimeFreq'
    start_time : datetime.datetime, optional
        starting time of the recordings
    chan_name : list of str, optional
        names of the channels
    n_chan : int, optional
        if chan_name is not specified, this defines the number of channels
    s_freq : int, optional
        sampling frequency
    time : numpy.ndarray or tuple of two numbers
        if tuple, the first and second numbers indicate beginning and end
    freq : numpy.ndarray or tuple of two numbers
        if tuple, the first and second numbers indicate beginning and end

    Returns
    -------
    data : instance of specified datatype

    Notes
    -----
    Data is generated using numpy.random.rand.

    """
    possible_datatypes = ('DataTime', 'DataFreq', 'DataTimeFreq')
    if datatype not in possible_datatypes:
        raise ValueError('Datatype should be one of ' +
                         ', '.join(possible_datatypes))

    if not s_freq:
        s_freq = 512

    if time:
        if isinstance(time, tuple) and len(time) == 2:
            time = arange(time[0], time[1], 1. / s_freq)
    else:
        time = arange(0, 1, 1. / s_freq)

    if freq:
        if isinstance(freq, tuple) and len(freq) == 2:
            freq = arange(freq[0], freq[1])
    else:
        freq = arange(0, s_freq / 2. + 1)

    if not chan_name:
        chan_name = ['chan{0:02}'.format(i) for i in range(n_chan)]

    if not start_time:
        start_time = datetime.now()

    if datatype == 'DataTime':
        data = DataTime()
        data.data = rand(len(chan_name), len(time))
    if datatype == 'DataFreq':
        data = DataFreq()
        data.data = rand(len(chan_name), 1, len(freq))
    if datatype == 'DataTimeFreq':
        data = DataTimeFreq()
        data.data = rand(len(chan_name), len(time), len(freq))

    data.chan_name = chan_name
    data.start_time = start_time
    data.s_freq = s_freq
    if datatype in ('DataTime', 'DataTimeFreq'):
        data.time = time
    if datatype in ('DataFreq', 'DataTimeFreq'):
        data.freq = freq

    return data
