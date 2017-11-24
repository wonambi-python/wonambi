from datetime import datetime
from logging import getLogger

from numpy import (abs, angle, arange, asarray, empty, exp, linspace,
                   pi, ptp, real, round, sin, zeros)
# numpy.random.random has an empty __module__ and sphinx autodoc adds it to api
from numpy import random
from numpy.fft import fft, ifft

from ..datatype import ChanTime, ChanFreq, ChanTimeFreq
from ..attr import Channels


lg = getLogger(__name__)


def create_data(datatype='ChanTime', n_trial=1, s_freq=256,
                chan_name=None, n_chan=8,
                time=None, freq=None, start_time=None,
                signal='random', amplitude=1, color=0, sine_freq=10,
                attr=None):
    """Create data of different datatype from scratch.

    Parameters
    ----------
    datatype : str
        one of 'ChanTime', 'ChanFreq', 'ChanTimeFreq'
    n_trial : int
        number of trials
    s_freq : int
        sampling frequency
    chan_name : list of str
        names of the channels
    n_chan : int
        if chan_name is not specified, this defines the number of channels
    time : numpy.ndarray or tuple of two numbers
        if tuple, the first and second numbers indicate beginning and end
    freq : numpy.ndarray or tuple of two numbers
        if tuple, the first and second numbers indicate beginning and end
    start_time : datetime.datetime, optional
        starting time of the recordings
    attr : list of str
        list of possible attributes (currently only 'channels')

    Only for datatype == 'ChanTime'
    signal : str
        'random', 'sine'
    amplitude : float
        amplitude (peak-to-peak) of the signal
    color : float
        noise color to generate (white noise is 0, pink is 1, brown is 2).
        This is only appropriate if signal == 'random'
    sine_freq : float
        frequency of the sine wave (only if signal == 'sine'), where phase
        is random for each channel

    Returns
    -------
    data : instance of specified datatype

    Notes
    -----
    ChanTime uses randn (to have normally distributed noise), while when you
    have freq, it uses random (which gives always positive values).
    You can only color noise for ChanTime, not for the other datatypes.
    """
    possible_datatypes = ('ChanTime', 'ChanFreq', 'ChanTimeFreq')
    if datatype not in possible_datatypes:
        raise ValueError('Datatype should be one of ' +
                         ', '.join(possible_datatypes))

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
        chan_name = _make_chan_name(n_chan)
    else:
        n_chan = len(chan_name)

    if start_time is None:
        start_time = datetime.now()

    if datatype == 'ChanTime':
        data = ChanTime()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):

            if signal == 'random':
                values = random.randn(*(len(chan_name), len(time)))
                for i_ch, x in enumerate(values):
                    values[i_ch, :] = _color_noise(x, s_freq, color)

            elif signal == 'sine':
                values = empty((n_chan, time.shape[0]))
                for i_ch in range(n_chan):
                    values[i_ch, :] = sin(2 * pi * sine_freq * time +
                                          random.randn())

            data.data[i] = values / ptp(values, axis=1)[:, None] * amplitude

    if datatype == 'ChanFreq':
        data = ChanFreq()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.data[i] = random.random((len(chan_name), len(freq)))

    if datatype == 'ChanTimeFreq':
        data = ChanTimeFreq()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.data[i] = random.random((len(chan_name), len(time), len(freq)))

    data.start_time = start_time
    data.s_freq = s_freq
    data.axis['chan'] = empty(n_trial, dtype='O')
    for i in range(n_trial):
        data.axis['chan'][i] = asarray(chan_name, dtype='U')

    if datatype in ('ChanTime', 'ChanTimeFreq'):
        data.axis['time'] = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.axis['time'][i] = time

    if datatype in ('ChanFreq', 'ChanTimeFreq'):
        data.axis['freq'] = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.axis['freq'][i] = freq

    if attr is not None:
        if 'chan' in attr:
            data.attr['chan'] = create_channels(data.chan[0])

    return data


def create_channels(chan_name=None, n_chan=None):
    """Create instance of Channels with random xyz coordinates

    Parameters
    ----------
    chan_name : list of str
        names of the channels
    n_chan : int
        if chan_name is not specified, this defines the number of channels

    Returns
    -------
    instance of Channels
        where the location of the channels is random
    """
    if chan_name is not None:
        n_chan = len(chan_name)

    elif n_chan is not None:
        chan_name = _make_chan_name(n_chan)

    else:
        raise TypeError('You need to specify either the channel names (chan_name) or the number of channels (n_chan)')

    xyz = round(random.randn(n_chan, 3) * 10, decimals=2)
    return Channels(chan_name, xyz)


def _color_noise(x, s_freq, coef=0):
    """Add some color to the noise by changing the power spectrum.

    Parameters
    ----------
    x : ndarray
        one vector of the original signal
    s_freq : int
        sampling frequency
    coef : float
        coefficient to apply (0 -> white noise, 1 -> pink, 2 -> brown,
                              -1 -> blue)

    Returns
    -------
    ndarray
        one vector of the colored noise.
    """
    # convert to freq domain
    y = fft(x)
    ph = angle(y)
    m = abs(y)

    # frequencies for each fft value
    freq = linspace(0, s_freq / 2, len(m) / 2 + 1)
    freq = freq[1:-1]

    # create new power spectrum
    m1 = zeros(len(m))
    # leave zero alone, and multiply the rest by the function
    m1[1:int(len(m) / 2)] = m[1:int(len(m) / 2)] * f(freq, coef)
    # simmetric around nyquist freq
    m1[int(len(m1) / 2 + 1):] = m1[1:int(len(m1) / 2)][::-1]

    # reconstruct the signal
    y1 = m1 * exp(1j * ph)
    return real(ifft(y1))


def f(x, coef):
    """Create an almost-linear function to apply to the power spectrum.

    Parameters
    ----------
    x : ndarray
        vector with the frequency values
    coef : float
        coefficient to apply (0 -> white noise, 1 -> pink, 2 -> brown,
                              -1 -> blue)

    Returns
    -------
    ndarray
        vector to multiply with the other frequencies

    Notes
    -----
    No activity in the frequencies below .1, to avoid huge distorsions.
    """
    y = 1 / (x ** coef)
    y[x < .1] = 0
    return y


def _make_chan_name(n_chan):
    return ['chan{0:02}'.format(i) for i in range(n_chan)]
