from datetime import datetime
from logging import getLogger

from numpy import (abs, angle, arange, around, asarray, empty, exp, linspace,
                   real, tile, zeros)
from numpy.random import random, randn
from numpy.fft import fft, ifft

from ..datatype import ChanTime, ChanFreq, ChanTimeFreq


lg = getLogger(__name__)


def create_data(datatype='ChanTime', start_time=None, n_trial=None,
                chan_name=None, n_chan=8, s_freq=None, time=None, freq=None,
                values=None, noise=0):
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
    noise : float or str, optional
        noise color to generate (white noise is 0, pink is 1, brown is 2). If
        str, then it can be 'ekg' (to create heart-related activity).
    values : tuple of two numbers, optional
        the min and max values of the random data values.

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

    if n_trial is None:
        n_trial = 1

    if s_freq is None:
        s_freq = 512

    if values is None:
        values = (-1, 1)
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
            if noise == 'ekg':
                n_sec = around(time[-1] - time[0])
                values = (tile(_make_ekg(s_freq), (len(chan_name), n_sec))
                          * mult + add)

            else:
                values = randn(*(len(chan_name), len(time))) * mult + add
                for i_ch, x in enumerate(values):
                    values[i_ch, :] = _color_noise(x, s_freq, noise)
            data.data[i] = values

    if datatype == 'ChanFreq':
        data = ChanFreq()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.data[i] = random((len(chan_name), len(freq))) * mult + add

    if datatype == 'ChanTimeFreq':
        data = ChanTimeFreq()
        data.data = empty(n_trial, dtype='O')
        for i in range(n_trial):
            data.data[i] = (random((len(chan_name), len(time), len(freq)))
                            * mult + add)

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

    return data


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


def _make_ekg(s_freq):
    """Create a simulated EKG of one second.

    Parameters
    ----------
    s_freq : int
        sampling frequency / duration of the sample

    Returns
    -------
    ndarray
        vector of length "s_freq" with one EKG in it, with peak at 1.

    Notes
    -----
    Based on ecg.m in Matlab, in the signal toolbox.
    """
    from scipy.signal import savgol_filter  # scipy is optional dependency

    EKG_val = asarray([0, 1, 40, 1, 0, -34, 118, -99, 0, 2, 21, 2, 0, 0, 0])
    EKG_time = asarray([0, 27, 59, 91, 131, 141, 163, 185, 195, 275, 307, 339,
                        357, 390, 440, 500])

    EKG_time = around(EKG_time * s_freq / EKG_time[-2])
    EKG_time[-1] = s_freq
    x = empty(s_freq)
    for i in range(len(EKG_val) - 1):
        m = arange(EKG_time[i], EKG_time[i + 1])
        slope = (EKG_val[i + 1] - EKG_val[i]) / (EKG_time[i + 1] - EKG_time[i])
        x[EKG_time[i]:EKG_time[i + 1]] = EKG_val[i] + slope * (m - EKG_time[i])

    polyorder = int(s_freq / 40 / 2) * 2 + 1
    x = savgol_filter(x, polyorder, 0)
    return x / max(x)
