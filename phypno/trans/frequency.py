from numpy import empty
from scipy.signal import periodogram
from ..datatype import DataFreq, DataTimeFreq
from ..trans import Select


class Freq:
    """Compute the power spectrum.

    Parameters
    ----------
    method : str
        the method to compute the power spectrum

    Attributes
    ----------
    method : str
        the method to compute the power spectrum

    """
    def __init__(self, method='periodogram'):
        self.method = method

    def __call__(self, data):
        freq = DataFreq()

        if self.method == 'periodogram':
            freq.s_freq = data.s_freq
            freq.chan_name = data.chan_name
            freq.start_time = data.start_time
            freq.data = empty((len(freq.chan_name),
                               int(data.s_freq / 2) + 1
                               ))

            for i_ch in range(data.data.shape[0]):
                f, Pxx = periodogram(data.data[i_ch, :],
                                     fs=data.s_freq,
                                     nfft=int(data.s_freq))
                freq.data[i_ch, :] = Pxx

            freq.freq = f

        return freq


class TimeFreq:
    """Compute the power spectrum over time.

    Parameters
    ----------
    toi : numpy.ndarray
        1d array with the time of interest.
    method : str, optional
        the method to compute the time-frequency representation, such as
        'stft' (short-time fourier transform).
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
            timefreq.time = self.toi

            calc_freq = Freq()

            timefreq.data = empty((len(timefreq.chan_name),
                                   len(timefreq.time),
                                   int(data.s_freq / 2) + 1
                                   ))

            for i_t, t in enumerate(self.toi):
                t1 = t - self.duration / 2
                t2 = t + self.duration / 2
                sel_time = Select(time=(t1, t2))

                freq = calc_freq(sel_time(data))
                timefreq.data[:, i_t, :] = freq.data

            timefreq.freq = freq.freq

        return timefreq
