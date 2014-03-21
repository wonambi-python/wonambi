from logging import getLogger
lg = getLogger('phypno')

from datetime import datetime

from numpy import arange, empty, asarray
from numpy.random import random

from ..datatype import ChanTime, ChanFreq, ChanTimeFreq


def create_data(datatype='ChanTime', start_time=None, n_trial=None,
                chan_name=None, n_chan=8, s_freq=None, time=None, freq=None,
                values=None):
    """Create data of different datatype from scratch.

    Parameters
    ----------
    datatype : str, optional
        one of 'ChanTime', 'ChanFreq', 'ChanTimeFreq'
    start_time : datetime.datetime, optional
        starting time of the recordings
    n_trial : int, optional
        number of trials
    chan_name : list of str, optional
        names of the channels
    n_chan : int, optional
        if chan_name is not specified, this defines the number of channels
    s_freq : int, optional
        sampling frequency
    time : numpy.ndarray or tuple of two numbers, optional
        if tuple, the first and second numbers indicate beginning and end
    freq : numpy.ndarray or tuple of two numbers, optional
        if tuple, the first and second numbers indicate beginning and end
    values : tuple of two numbers, optional
        the min and max values of the random data values.

    Returns
    -------
    data : instance of specified datatype

    Notes
    -----
    Data is generated using numpy.random.random, meaning that the values will
    be between values[0] (included) and values[1] (excluded).

    """
    possible_datatypes = ('ChanTime', 'ChanFreq', 'ChanTimeFreq')
    if datatype not in possible_datatypes:
        raise ValueError('Datatype should be one of ' +
                         ', '.join(possible_datatypes))

    if n_trial is None:
        n_trial = 1

    if s_freq is None:
        s_freq = 512

    if values is None:
        values = (0, 1)
    mult = values[1] - values[0]
    add = values[0]

    if time is not None:
        if isinstance(time, tuple) and len(time) == 2:
            time = arange(time[0], time[1], 1. / s_freq)
    else:
        time = arange(0, 1, 1. / s_freq)

    if freq is not None:
        if isinstance(freq, tuple) and len(freq) == 2:
            freq = arange(freq[0], freq[1])
    else:
        freq = arange(0, s_freq / 2. + 1)

    if chan_name is None:
        chan_name = ['chan{0:02}'.format(i) for i in range(n_chan)]

    if start_time is None:
        start_time = datetime.now()

    if datatype == 'ChanTime':
        data = ChanTime()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.data[i] = random((len(chan_name), len(time))) * mult + add
    if datatype == 'ChanFreq':
        data = ChanFreq()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.data[i] = random((len(chan_name), 1, len(freq))) * mult + add
    if datatype == 'ChanTimeFreq':
        data = ChanTimeFreq()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.data[i] = (random((len(chan_name), len(time), len(freq)))
                            * mult + add)

    data.start_time = start_time
    data.s_freq = s_freq
    data.dim['chan'] = empty(n_trial, dtype='O')
    for i in range(n_trial):
        data.dim['chan'][i] = asarray(chan_name, dtype='U')

    if datatype in ('ChanTime', 'ChanTimeFreq'):
        data.dim['time'] = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.dim['time'][i] = time

    if datatype in ('ChanFreq', 'ChanTimeFreq'):
        data.dim['freq'] = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.dim['freq'][i] = freq

    return data
