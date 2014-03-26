from numpy import empty
from scipy.signal import welch
from ..datatype import ChanFreq, ChanTimeFreq


class Freq:
    """Compute the power spectrum.

    Parameters
    ----------
    method : str
        the method to compute the power spectrum, such as 'welch'

    Attributes
    ----------
    method : str
        the method to compute the power spectrum

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
            future on other axis, but I cannot imagine how.

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
        'stft' (short-time fourier transform).
    toi : numpy.ndarray
        1d array with the time of interest.
    duration : float, optional
        length/duration in s to compute fourier-transform.

    Attributes
    ----------
    method : str
        the method to compute the time-frequency representation.

    """
    def __init__(self, toi, method='stft', duration=1):
        self.method = method
        self.toi = toi
        self.duration = duration

    def __call__(self, data):
        timefreq = DataTimeFreq()

        if self.method == 'stft':
            timefreq.s_freq = data.s_freq
            timefreq.chan_name = data.chan_name
            timefreq.start_time = data.start_time

            timefreq.data = empty(len(data.data), dtype='O')
            timefreq.time = empty(len(data.data), dtype='O')
            timefreq.freq = empty(len(data.data), dtype='O')

            for i in range(len(data.data)):
                timefreq.time[i] = self.toi

                timefreq.data[i] = empty((len(timefreq.chan_name),
                                          len(self.toi),
                                          int(data.s_freq / 2) + 1
                                          ))

        return timefreq
