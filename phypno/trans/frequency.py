"""Module to compute frequency representation.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import arange, empty, where
from scipy.signal import welch, morlet, fftconvolve

from ..datatype import ChanFreq, ChanTimeFreq


class Freq:
    """Compute the power spectrum.

    Parameters
    ----------
    method : str
        the method to compute the power spectrum, such as 'welch'

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
        M_in_s : int
            duration of the wavelet in seconds
        w : int
            Omega0
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
                               'M_in_s': 1,
                               'w': 5,
                               }
        elif method == 'welch':
            default_options = {'duration': 1,
                               'overlap': .5,
                               }

        self.method = method
        default_options.update(options)
        for name, value in default_options.items():
            if value is None:
                raise ValueError('Specify a value for ' + name)
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
            wavelets = _create_morlet(self.options, data.s_freq)

            for i in range(data.number_of('trial')):
                lg.info('Processing trial # {0: 6}'.format(i))
                timefreq.axis['freq'][i] = self.options['foi']

                timefreq.data[i] = empty((data.number_of('chan')[i],
                                          data.number_of('time')[i],
                                          len(self.options['foi'])),
                                         dtype='complex')
                for i_c, chan in enumerate(data.axis['chan'][i]):
                    dat = data(trial=i, chan=chan)
                    for i_f, f in enumerate(self.options['foi']):
                        tf = fftconvolve(dat, wavelets[i_f, :], 'same')
                        timefreq.data[i][i_c, :, i_f] = tf

        elif self.method == 'welch':

            for i, trial in enumerate(data):
                time_in_trl = trial.axis['time'][0]
                overlap = self.options['overlap'] * self.options['duration']
                windows = arange(time_in_trl[0], time_in_trl[-1], overlap)
                windows = windows[1:]  # remove first one
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

    Notes
    -----
    Wavelets are not scaled by the frequency.

    """
    M = options['M_in_s'] * s_freq

    wavelets = empty((len(options['foi']), M), dtype='complex')
    for i, f in enumerate(options['foi']):
        scaling = _compute_scaling(f, M, options['w'], s_freq)
        wavelets[i, :] = morlet(M, options['w'], scaling)

    return wavelets


def _compute_scaling(f, M, w, r):
    """Compute the scaling factor for a specific frequency.

    Parameters
    ----------
    f : int or float
        frequency of interest
    M : int
        duration of the wavelet in samples
    w : int
        Omega0 (wavelet parameter)
    r : int or float
        sampling frequency of the data

    Returns
    -------
    float
        scaling factor

    """
    return (M * f) / (2 * w * r)
