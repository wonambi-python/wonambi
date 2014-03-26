"""Module to compute frequency representation.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import empty
from scipy.signal import welch, morlet, convolve

from ..datatype import ChanFreq, ChanTimeFreq


class Freq:
    """Compute the power spectrum.

    Parameters
    ----------
    method : str
        the method to compute the power spectrum, such as 'welch'

    """
    def __init__(self, method='welch', **options):
        implemented_methods = ('welch', )

        if method not in implemented_methods:
            raise ValueError('Method ' + method + ' is not implemented yet.\n'
                             'Currently implemented methods are ' +
                             ', '.join(implemented_methods))

        self.method = method
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
        'morlet' (wavelet using complex morlet window)
    foi : ndarray or list or tuple
        vector with frequency of interest
    options : dict
        Options depends on the method.

    Notes
    -----
    For method 'morlet', the following options are specified:
      - M_in_s : duration of the wavelet in seconds
      - w : Omega0

    """
    def __init__(self, method='morlet', foi=None, **options):
        implemented_methods = ('morlet', )

        if method not in implemented_methods:
            raise ValueError('Method ' + method + ' is not implemented yet.\n'
                             'Currently implemented methods are ' +
                             ', '.join(implemented_methods))

        self.method = method
        if foi is None:
            raise ValueError('Specify a value for the frequency of interest')
        self.foi = foi

        if method == 'morlet':
            default_options = {'M_in_s': 1,
                               'w': 5,
                               }
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
        timefreq = ChanTimeFreq()
        timefreq.s_freq = data.s_freq
        timefreq.start_time = data.start_time
        timefreq.axis['chan'] = data.axis['chan']
        timefreq.axis['time'] = data.axis['time']
        timefreq.axis['freq'] = empty(data.number_of('trial'), dtype='O')
        timefreq.data = empty(data.number_of('trial'), dtype='O')

        if self.method == 'morlet':
            wavelets = _create_morlet(self.foi, data.s_freq, self.options)

            for i in range(data.number_of('trial')):
                lg.info('Processing trial # {0: 6}'.format(i))
                timefreq.axis['freq'][i] = self.foi

                timefreq.data[i] = empty((data.number_of('chan')[i],
                                          data.number_of('time')[i],
                                          len(self.foi)),
                                          dtype='complex')
                for i_c, chan in enumerate(data.axis['chan'][i]):
                    dat = data(trial=i, chan=chan)
                    for i_f, f in enumerate(self.foi):
                        tf = convolve(dat, wavelets[i_f, :], 'same')
                        timefreq.data[i][i_c, :, i_f] = tf

        return timefreq


def _create_morlet(foi, s_freq, options):
    """Create morlet wavelets, with scipy.signal doing the actula computation.

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

    wavelets = empty((len(foi), M), dtype='complex')
    for i, f in enumerate(foi):
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
