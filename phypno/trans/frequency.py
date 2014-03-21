from numpy import empty, squeeze
from scipy.signal import periodogram
from ..datatype import ChanFreq, ChanTimeFreq
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

            freq.data = empty(len(data.data), dtype='O')
            freq.freq = empty(len(data.data), dtype='O')
            for i in range(len(data.data)):
                freq.data[i] = empty((len(freq.chan_name),
                                      1,
                                      int(data.s_freq / 2) + 1))

                for i_ch in range(data.data[i].shape[0]):
                    f, Pxx = periodogram(data.data[i][i_ch, :],
                                         fs=data.s_freq,
                                         nfft=int(data.s_freq))
                    freq.data[i][i_ch, 0, :] = Pxx
                freq.freq[i] = f

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

            timefreq.data = empty(len(data.data), dtype='O')
            timefreq.time = empty(len(data.data), dtype='O')
            timefreq.freq = empty(len(data.data), dtype='O')

            for i in range(len(data.data)):
                timefreq.time[i] = self.toi

                timefreq.data[i] = empty((len(timefreq.chan_name),
                                          len(self.toi),
                                          int(data.s_freq / 2) + 1
                                          ))

        """This is too hard at the moment, and I don't need it probably.

            for i_t, t in enumerate(self.toi):
                t1 = t - self.duration / 2
                t2 = t + self.duration / 2
                sel_time = Select(time=(t1, t2))

                for i_ch in range(data.data[i].shape[0]):
                    f, Pxx = periodogram(data.data[i][i_ch, :],
                                         fs=data.s_freq,
                                         nfft=int(data.s_freq))
                    freq.data[i][i_ch, 0, :] = Pxx

                timefreq.data[:, i_t, :] = squeeze(freq.data[0], axis=1)

                timefreq.freq[i] = freq.freq[i]
        """

        return timefreq
