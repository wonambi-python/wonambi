from __future__ import division
from copy import deepcopy
from logging import getLogger
from scipy.signal import butter, filtfilt

lg = getLogger('phypno')


class Filter:
    """Design filter and apply it.

    Parameters
    ----------
    low_cut : float, optional
        low cutoff for high-pass filter
    high_cut : float, optional
        high cutoff for low-pass filter
    order : int, optional
        filter order
    s_freq : float, optional
        sampling frequency

    Attributes
    ----------
    b, a : numpy.ndarray
        filter values
    info : dict
        information about type, order, and cut-off of the filter.

    Notes
    -----
    At the moment, it only uses a butterworth filter.

    If you specify low_cut only, it generates a high-pass filter.
    If you specify high_cut only, it generates a low-pass filter.
    If you specify both, it generates a band-pass filter.

    low_cut and high_cut should be given as ratio of the Nyquist. But if you
    specify s_freq, then the ratio will be computed automatically.

    """
    def __init__(self, low_cut=None, high_cut=None, order=4, s_freq=None):

        if s_freq is not None:
            nyquist = s_freq / 2.
        else:
            nyquist = 1

        btype = None
        if low_cut is not None and high_cut is not None:
            btype = 'bandpass'
            Wn = (low_cut / nyquist,
                  high_cut / nyquist)
        elif low_cut is not None:
            btype = 'highpass'
            Wn = low_cut / nyquist
        elif high_cut is not None:
            btype = 'lowpass'
            Wn = high_cut / nyquist

        if not btype:
            raise TypeError('You should specify at least low_cut or high_cut')

        try:
            freq = '-'.join([str(x) for x in Wn])
        except TypeError:
            freq = str(Wn)

        self.info = {'order': order,
                     'type': btype,
                     'freq': freq}

        lg.debug('order {0: 2}, Wn {1}, btype {2}'.format(order, str(Wn),
                                                          btype))
        b, a = butter(order, Wn, btype=btype)
        self.b = b
        self.a = a

    def __call__(self, data):
        """Apply the filter to the data.

        Parameters
        ----------
        data : instance of DataRaw
            the data to filter

        Returns
        -------
        filtered_data : instance of DataRaw
            filtered data

        """
        fdata = deepcopy(data)
        for i in range(len(data.data)):
            fdata.data[i] = filtfilt(self.b, self.a, data.data[i])
        return fdata
