"""Module to compute frequency representation.
"""
from copy import deepcopy
from logging import getLogger
from warnings import warn

from numpy import (arange, array, empty, exp, inf, max, mean, pi, real, sqrt,
                   swapaxes)
from numpy.linalg import norm
from scipy.signal import welch, fftconvolve, spectrogram
try:
    from mne.time_frequency.multitaper import multitaper_psd
except ImportError:
    pass

from ..datatype import ChanFreq, ChanTimeFreq

lg = getLogger(__name__)


def frequency(data, method='welch', **options):
    """Compute the power spectrum.

    Parameters
    ----------
    method : str
        the method to compute the power spectrum, such as 'welch'
    data : instance of ChanTime
        one of the datatypes

    Returns
    -------
    instance of ChanFreq

    Raises
    ------
    TypeError
        If the data does not have a 'time' axis. It might work in the
        future on other axes, but I cannot imagine how.

    Notes
    -----
    It uses sampling frequency as specified in s_freq, it does not
    recompute the sampling frequency based on the time axis.

    For method 'welch', the following options should be specified:
        duraton : int
            duration of the window to compute the power spectrum, in s
        overlap : int
            amount of overlap (0 -> no overlap, 1 -> full overlap)
        window : str or tuple or array
            desired window to use
        detrend : str or function or False
            specifies how to detrend each segment
        scaling : str
            you can choose between density (V**2/Hz) or spectrum (V**2)

        The output is real PSD, not complex, because of
        https://github.com/scipy/scipy/issues/5757
    """
    implemented_methods = ('welch', 'multitaper')

    if method not in implemented_methods:
        raise ValueError('Method ' + method + ' is not implemented yet.\n'
                         'Currently implemented methods are ' +
                         ', '.join(implemented_methods))

    if method == 'welch':
        default_options = {'duration': 1,
                           'overlap': 0.5,
                           'window': 'hann',
                           'detrend': 'constant',
                           'scaling': 'density',
                           }

    elif method == 'multitaper':
        default_options = {'fmin': 0,
                           'fmax': inf,
                           'bandwidth': None,
                           'adaptive': False,
                           'low_bias': True,
                           'normalization': 'full',
                           }

    default_options.update(options)
    options = default_options

    if 'time' not in data.list_of_axes:
        raise TypeError('\'time\' is not in the axis ' +
                        str(data.list_of_axes))
    idx_time = data.index_of('time')

    freq = ChanFreq()
    freq.s_freq = data.s_freq
    freq.start_time = data.start_time
    freq.axis['chan'] = data.axis['chan']
    freq.axis['freq'] = empty(data.number_of('trial'), dtype='O')
    freq.data = empty(data.number_of('trial'), dtype='O')

    for i in range(data.number_of('trial')):
        if method == 'welch':
            nperseg = int(options['duration'] * data.s_freq)
            noverlap = int(options['overlap'] * nperseg)
            f, Pxx = welch(data(trial=i),
                           fs=data.s_freq,
                           nperseg=nperseg,
                           noverlap=noverlap,
                           scaling=options['scaling'],
                           axis=idx_time)

        elif method == 'multitaper':
            Pxx, f = multitaper_psd(data(trial=i),
                                    sfreq=data.s_freq,
                                    fmin=options['fmin'],
                                    fmax=options['fmax'],
                                    bandwidth=options['bandwidth'],
                                    adaptive=options['adaptive'],
                                    low_bias=options['low_bias'],
                                    normalization=options['normalization'],
                                    n_jobs=2)
        freq.axis['freq'][i] = f
        freq.data[i] = Pxx

    return freq


def timefrequency(data, method='morlet', time_skip=1, **options):
    """Compute the power spectrum over time.

    Parameters
    ----------
    method : str, optional
        the method to compute the time-frequency representation, such as
        'morlet' (wavelet using complex morlet window), 'spectrogram' (relies
        on scipy implementation)
    options : dict
        Options depends on the method.
    data : instance of ChanTime
        data to analyze

    Returns
    -------
    instance of ChanTimeFreq
        data in time-frequency representation.

    Examples
    --------
    The data in ChanTimeFreq are complex and they should stay that way. You
    can also get the magnitude or power the easy way using Math.

    >>> from wonambi.trans import math, timefreq
    >>> tf = timefreq(data, foi=(8, 10))
    >>> tf_abs = math(tf, operator_name='abs')
    >>> tf_abs.data[0][0, 0, 0]
    1737.4662329214384)

    Notes
    -----
    It uses sampling frequency as specified in s_freq, it does not
    recompute the sampling frequency based on the time axis.

    For method 'morlet', the following options should be specified:
        foi : ndarray or list or tuple
            vector with frequency of interest
        ratio : float
            ratio for a wavelet family ( = freq / sigma_f)
        sigma_f : float
            standard deviation of the wavelet in frequency domain
        dur_in_sd : float
            duration of the wavelet, given as number of the standard deviation
            in the time domain, in one side.
        dur_in_s : float
            total duration of the wavelet, two-sided (i.e. from start to
            finish)
        time_skip : int, in samples
            number of time points to skip (it runs convolution on all the
            data points, but you don't need to store them all)
        normalization : str
            'area' means that energy is normalized to 1, 'peak' means that the
            peak of the wavelet is set at 1, 'max' is a normalization used by
            nitime where the max value of the output of the convolution remains
            the same even if you change the sigma_f.
        zero_mean : bool
            make sure that the wavelet has zero mean (only relevant if ratio
            < 5)

    For method 'spectrogram', the following options should be specified:
        duraton : int
            duration of the window to compute the power spectrum, in s
        overlap : int
            amount of overlap (0 -> no overlap, 1 -> full overlap)
        window : str or tuple or array
            desired window to use
        detrend : str or function or False
            specifies how to detrend each segment
        scaling : str
            you can choose between density (V**2/Hz) or spectrum (V**2)
    """
    implemented_methods = ('morlet', 'spectrogram')

    if method not in implemented_methods:
        raise ValueError('Method ' + method + ' is not implemented yet.\n'
                         'Currently implemented methods are ' +
                         ', '.join(implemented_methods))

    if method == 'morlet':
        default_options = {'foi': None,
                           'ratio': 5,
                           'sigma_f': None,
                           'dur_in_sd': 4,
                           'dur_in_s': None,
                           'normalization': 'area',
                           'zero_mean': False,
                           }
    elif method == 'spectrogram':
        default_options = {'duration': 1,
                           'overlap': 0.5,
                           'window': 'hann',
                           'detrend': 'constant',
                           'scaling': 'density',
                           }

    default_options.update(options)
    options = default_options

    timefreq = ChanTimeFreq()
    timefreq.s_freq = data.s_freq
    timefreq.start_time = data.start_time
    timefreq.axis['chan'] = data.axis['chan']
    timefreq.axis['time'] = empty(data.number_of('trial'), dtype='O')
    timefreq.axis['freq'] = empty(data.number_of('trial'), dtype='O')
    timefreq.data = empty(data.number_of('trial'), dtype='O')

    if method == 'morlet':

        wavelets = _create_morlet(deepcopy(options), data.s_freq)

        for i in range(data.number_of('trial')):
            lg.info('Processing trial # {0: 6}'.format(i))
            timefreq.axis['freq'][i] = array(options['foi'])
            timefreq.axis['time'][i] = data.axis['time'][i][::time_skip]

            timefreq.data[i] = empty((data.number_of('chan')[i],
                                      data.number_of('time')[i] // time_skip,
                                      len(options['foi'])),
                                     dtype='complex')
            for i_c, chan in enumerate(data.axis['chan'][i]):
                dat = data(trial=i, chan=chan)
                for i_f, wavelet in enumerate(wavelets):
                    tf = fftconvolve(dat, wavelet, 'same')
                    timefreq.data[i][i_c, :, i_f] = tf[::time_skip]

        if time_skip != 1:
            warn('sampling frequency in s_freq refers to the input data, '
                 'not to the timefrequency output')

    elif method == 'spectrogram':
        nperseg = int(options['duration'] * data.s_freq)
        noverlap = int(options['overlap'] * nperseg)

        for i, trial in enumerate(data):
            f, t, Sxx = spectrogram(trial(0), fs=data.s_freq,
                                    window=options['window'],
                                    nperseg=nperseg,
                                    noverlap=noverlap,
                                    detrend=options['detrend'],
                                    scaling=options['scaling'],
                                    mode='complex',
                                    axis=data.index_of('time'))

            # the last axis of Sxx corresponds to the segment times
            timefreq.data[i] = swapaxes(Sxx[..., ::time_skip], -1, -2)
            # add offset
            timefreq.axis['time'][i] = t[::time_skip] + data.axis['time'][i][0]
            timefreq.axis['freq'][i] = f

    return timefreq


def _create_morlet(options, s_freq):
    """Create morlet wavelets, with scipy.signal doing the actual computation.

    Parameters
    ----------
    foi : ndarray or list or tuple
        vector with frequency of interest
    s_freq : int or float
        sampling frequency of the data
    options : dict
        with 'M_in_s' (duration of the wavelet in seconds) and 'w' (Omega0)

    Returns
    -------
    ndarray
        nFreq X nSamples matrix containing the complex Morlet wavelets.

    """
    wavelets = []
    foi = options.pop('foi')
    for f in foi:
        wavelets.append(morlet(f, s_freq, **options))

    return wavelets


def morlet(freq, s_freq, ratio=5, sigma_f=None, dur_in_sd=4, dur_in_s=None,
           normalization='peak', zero_mean=False):
    """Create a Morlet wavelet.

    Parameters
    ----------
    freq : float
        central frequency of the wavelet
    s_freq : int
        sampling frequency
    ratio : float
        ratio for a wavelet family ( = freq / sigma_f)
    sigma_f : float
        standard deviation of the wavelet in frequency domain
    dur_in_sd : float
        duration of the wavelet, given as number of the standard deviation in
        the time domain, in one side.
    dur_in_s : float
        total duration of the wavelet, two-sided (i.e. from start to finish)
    normalization : str
        'area' means that energy is normalized to 1, 'peak' means that the peak
        is set at 1, 'max' is a normalization used by nitime which does not
        change max value of output when you change sigma_f.
    zero_mean : bool
        make sure that the wavelet has zero mean (only relevant if ratio < 5)

    Returns
    -------
    ndarray
        vector containing the complex Morlet wavelets

    Notes
    -----
    'ratio' and 'sigma_f' are mutually exclusive. If you use 'sigma_f', the
    standard deviation stays the same for all the frequency. It's more common
    to specify a constant ratio for the wavelet family, so that the frequency
    resolution changes with the frequency of interest.

    'dur_in_sd' and 'dur_in_s' are mutually exclusive. 'dur_in_s' specifies the
    total duration (from start to finish) of the window. 'dur_in_sd' calculates
    the total duration as the length in standard deviations in the time domain:
    dur_in_s = dur_in_sd * 2 * sigma_t, with sigma_t = 1 / (2 * pi * sigma_f)
    """
    if sigma_f is None:
        sigma_f = freq / ratio
    else:
        ratio = freq / sigma_f
    sigma_t = 1 / (2 * pi * sigma_f)

    if ratio < 5 and not zero_mean:
        lg.info('The wavelet won\'t have zero mean, set zero_mean=True to '
                'correct it')

    if dur_in_s is None:
        dur_in_s = sigma_t * dur_in_sd * 2

    t = arange(-dur_in_s / 2, dur_in_s / 2, 1 / s_freq)

    w = exp(1j * 2 * pi * freq * t)
    if zero_mean:
        w -= exp(-1 / 2 * ratio ** 2)

    w *= exp(-t ** 2 / (2 * sigma_t ** 2))

    if normalization == 'area':
        w /= sqrt(sqrt(pi) * sigma_t * s_freq)
    elif normalization == 'max':
        w /= 2 * sigma_t * sqrt(2 * pi) / s_freq
    elif normalization == 'peak':
        pass

    lg.info('At freq {0: 9.3f}Hz, sigma_f={1: 9.3f}Hz, sigma_t={2: 9.3f}s, '
            'total duration={3: 9.3f}s'.format(freq, sigma_f, sigma_t,
                                               dur_in_s))
    lg.debug('    Real peak={0: 9.3f}, Mean={1: 12.6f}, '
             'Energy={2: 9.3f}'.format(max(real(w)), mean(w), norm(w) ** 2))

    return w
