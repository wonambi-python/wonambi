"""Module to compute frequency representation.

"""
from logging import getLogger, DEBUG
lg = getLogger('phypno')

from copy import deepcopy

from numpy import arange, empty, exp, max, mean, pi, real, sqrt, where
from numpy.linalg import norm
from scipy.signal import welch, fftconvolve

from ..datatype import ChanFreq, ChanTimeFreq


class Freq:
    """Compute the power spectrum.

    Parameters
    ----------
    method : str
        the method to compute the power spectrum, such as 'welch'

    Notes
    -----
    TODO: check that power does not change if duration becomes longer
    """
    def __init__(self, method='welch', duration=2, **options):
        implemented_methods = ('welch', )

        if method not in implemented_methods:
            raise ValueError('Method ' + method + ' is not implemented yet.\n'
                             'Currently implemented methods are ' +
                             ', '.join(implemented_methods))

        self.method = method
        self.duration = duration
        self.options = options

    def __call__(self, data):
        """Calculate power on the data.

        Parameters
        ----------
        data : instance of ChanTime
            one of the datatypes

        Returns
        -------
        instance of ChanFreq

        Notes
        -----
        It uses sampling frequency as specified in s_freq, it does not
        recompute the sampling frequency based on the time axis.

        Raises
        ------
        TypeError
            If the data does not have a 'time' axis. It might work in the
            future on other axes, but I cannot imagine how.

        """
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

        if self.method == 'welch':
            for i in range(data.number_of('trial')):

                f, Pxx = welch(data(trial=i),
                               fs=data.s_freq,
                               nperseg=data.s_freq * self.duration,
                               axis=idx_time,
                               **self.options)
                freq.axis['freq'][i] = f
                freq.data[i] = Pxx

        return freq


class TimeFreq:
    """Compute the power spectrum over time.

    Parameters
    ----------
    method : str, optional
        the method to compute the time-frequency representation, such as
        'morlet' (wavelet using complex morlet window), 'welch' (compute
        power spectrum for each window, but it does not average them)
    options : dict
        Options depends on the method.

    Notes
    -----
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
        normalization : str
            'area' means that energy is normalized to 1, 'peak' means that the
            peak is set at 1, 'max' is a normalization used by nitime that I
            don't understand.
        zero_mean : bool
            make sure that the wavelet has zero mean (only relevant if ratio
            < 5)

    For method 'welch', the following options should be specified:
        duraton : int
            duration of the window to compute the power spectrum, in s
        overlap : int
            amount of overlap between windows

    """
    def __init__(self, method='morlet', **options):
        implemented_methods = ('morlet', 'welch')

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
        elif method == 'welch':
            default_options = {'duration': 1,
                               'overlap': .5,
                               }

        self.method = method
        default_options.update(options)
        self.options = default_options

    def __call__(self, data):
        """Compute the time-frequency analysis.

        Parameters
        ----------
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

        >>> from phypno.trans import Math, TimeFreq
        >>> calc_tf = TimeFreq(foi=(8, 10))
        >>> tf = calc_tf(data)
        >>> make_abs = Math(operator_name='abs')
        >>> tf_abs = make_abs(tf)
        >>> tf_abs.data[0][0, 0, 0]
        1737.4662329214384)

        """
        idx_time = data.index_of('time')

        timefreq = ChanTimeFreq()
        timefreq.s_freq = data.s_freq
        timefreq.start_time = data.start_time
        timefreq.axis['chan'] = data.axis['chan']
        timefreq.axis['time'] = empty(data.number_of('trial'), dtype='O')
        timefreq.axis['freq'] = empty(data.number_of('trial'), dtype='O')
        timefreq.data = empty(data.number_of('trial'), dtype='O')

        if self.method == 'morlet':

            wavelets = _create_morlet(deepcopy(self.options), data.s_freq)

            for i in range(data.number_of('trial')):
                lg.info('Processing trial # {0: 6}'.format(i))
                timefreq.axis['freq'][i] = self.options['foi']
                timefreq.axis['time'][i] = data.axis['time'][i]

                timefreq.data[i] = empty((data.number_of('chan')[i],
                                          data.number_of('time')[i],
                                          len(self.options['foi'])),
                                         dtype='complex')
                for i_c, chan in enumerate(data.axis['chan'][i]):
                    dat = data(trial=i, chan=chan)
                    for i_f, wavelet in enumerate(wavelets):
                        tf = fftconvolve(dat, wavelet, 'same')
                        timefreq.data[i][i_c, :, i_f] = tf

        elif self.method == 'welch':

            for i, trial in enumerate(data):
                time_in_trl = trial.axis['time'][0]
                half_duration = self.options['duration'] / 2
                overlap = self.options['overlap'] * half_duration
                windows = arange(time_in_trl[0], time_in_trl[-1], overlap)

                good_win = (windows - half_duration) > time_in_trl[0]
                windows = windows[good_win]
                good_win = (windows + half_duration) < time_in_trl[-1]
                windows = windows[good_win]

                timefreq.axis['time'][i] = windows

                n_sel_time = self.options['duration'] * data.s_freq
                n_freq = n_sel_time / 2 + 1

                timefreq.data[i] = empty((data.number_of('chan')[i],
                                          len(windows), n_freq))

                for i_win, win_value in enumerate(windows):
                    # this is necessary to go around the floating point errors
                    # instead of checking the intervals with >= and <,
                    # we first find the first point and move from there
                    time0 = win_value - self.options['duration'] / 2
                    i_time0 = where(time_in_trl >= time0)[0][0]
                    i_time1 = i_time0 + n_sel_time

                    x = trial(trial=0, time=time_in_trl[i_time0:i_time1])
                    f, Pxx = welch(x,
                                   fs=data.s_freq,
                                   nperseg=x.shape[idx_time],
                                   axis=idx_time)
                    timefreq.data[i][:, i_win, :] = Pxx

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
        is set at 1, 'max' is a normalization used by nitime that I don't
        understand.
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

    if lg.level == DEBUG:
        lg.debug('At freq {0:.2f}Hz, sigma_f={1:.2f}Hz, sigma_t={2:.3f}s, '
                 'total duration={3:.3f}s'.format(freq, sigma_f, sigma_t,
                                                  dur_in_s))
        lg.debug('    Real peak={0:.3f}, Mean={1:.6f}, '
                 'Energy={2:.3f}'.format(max(real(w)), mean(w), norm(w) ** 2))

    return w
