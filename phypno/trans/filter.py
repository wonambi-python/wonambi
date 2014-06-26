"""Module to filter the data.

"""
from logging import getLogger
lg = getLogger('phypno')

from copy import deepcopy
from itertools import product

from numpy import ix_, expand_dims, squeeze
from numpy.linalg import norm
from scipy.signal import iirfilter, filtfilt, get_window, fftconvolve


class Filter:
    """Design filter and apply it.

    Parameters
    ----------
    ftype : str
        'butter', 'cheby1', 'cheby2', 'ellip', 'bessel' or 'diff'
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
    You can specify any filter type as defined by iirfilter.

    If you specify low_cut only, it generates a high-pass filter.
    If you specify high_cut only, it generates a low-pass filter.
    If you specify both, it generates a band-pass filter.

    low_cut and high_cut should be given as ratio of the Nyquist. But if you
    specify s_freq, then the ratio will be computed automatically.

    """
    def __init__(self, low_cut=None, high_cut=None, order=4, ftype='butter',
                 s_freq=None, Rs=None):

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

        if Rs is None:
            Rs = 40

        self.info = {'order': order,
                     'btype': btype,
                     'ftype': ftype,
                     'freq': freq,
                     }

        lg.debug('order {0: 2}, Wn {1}, btype {2}, ftype {3}'
                 ''.format(order, str(Wn), btype, ftype))
        b, a = iirfilter(order, Wn, btype=btype, ftype=ftype, rs=Rs)
        self.b = b
        self.a = a

    def __call__(self, data, axis='time'):
        """Apply the filter to the data.

        Parameters
        ----------
        data : instance of Data
            the data to filter.
        axis : str, optional
            axis to apply the filter on.

        Returns
        -------
        filtered_data : instance of DataRaw
            filtered data

        """
        fdata = deepcopy(data)
        for i in range(data.number_of('trial')):
            fdata.data[i] = filtfilt(self.b, self.a,
                                     data.data[i],
                                     axis=data.index_of(axis))
        return fdata


class Convolve:
    """Design taper and convolve it with the signal.

    Parameters
    ----------
    window : str
        one of the windows in scipy, using get_window
    length : float, optional
        length of the window
    s_freq : float, optional
        sampling frequency

    Attributes
    ----------
    taper : numpy.ndarray
        the actual taper used for the convolution

    See Also
    --------
    scipy.signal.get_window : function used to create windows

    Notes
    -----
    Taper is normalized such that the integral of the function remains the
    same even after convolution.

    """
    def __init__(self, window, length=1, s_freq=None):
        taper = get_window(window, length * s_freq)
        self.taper = taper / sum(taper)

    def __call__(self, data, axis='time'):
        """Apply the filter to the data.

        Parameters
        ----------
        data : instance of Data
            the data to filter.
        axis : str, optional
            axis to apply the filter on.

        Returns
        -------
        filtered_data : instance of DataRaw
            filtered data

        Notes
        -----
        Most of the code is identical to fftconvolve(axis=data.index_of(axis))
        but unfortunately fftconvolve in scipy 0.13 doesn't take that argument
        so we need to redefine it here. It's pretty slow too.

        """
        fdata = deepcopy(data)
        idx_axis = data.index_of(axis)

        for i in range(data.number_of('trial')):

            sel_dim = []
            i_dim = []
            for i_axis, one_axis in enumerate(data.list_of_axes):
                if one_axis != axis:
                    i_dim.append(i_axis)
                    sel_dim.append(range(data.number_of(one_axis)[i]))

            for one_iter in product(*sel_dim):
                # create the numpy indices for one value per dimension,
                # except for the dimension of interest
                idx = [[x] for x in one_iter]
                idx.insert(idx_axis, range(data.number_of(axis)[0]))
                indices = ix_(*idx)

                d_1dim = squeeze(data.data[0][indices],
                                 axis=i_dim)

                d_1dim = fftconvolve(d_1dim, self.taper, 'same')

                for to_squeeze in i_dim:
                    d_1dim = expand_dims(d_1dim, axis=to_squeeze)
                fdata.data[0][indices] = d_1dim

        return fdata
