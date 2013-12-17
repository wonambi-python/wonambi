from numpy import empty
from scipy.signal import periodogram
from ..datatype import DataFreq, DataTimeFreq


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
    def __init__(self):
        pass

    def __call__(self, data):
        pass
