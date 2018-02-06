"""Module to filter the data.
"""
from logging import getLogger

from itertools import product

from numpy import empty, ix_, expand_dims, squeeze
from scipy.signal import iirfilter, filtfilt, get_window, fftconvolve

lg = getLogger(__name__)


def filter_(data, axis='time', low_cut=None, high_cut=None, order=4,
            ftype='butter', Rs=None):
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
    You can specify any filter type as defined by iirfilter.

    If you specify low_cut only, it generates a high-pass filter.
    If you specify high_cut only, it generates a low-pass filter.
    If you specify both, it generates a band-pass filter.

    low_cut and high_cut should be given as ratio of the Nyquist. But if you
    specify s_freq, then the ratio will be computed automatically.

    Raises
    ------
    ValueError
        if the cutoff frequency is larger than the Nyquist frequency.
    """
    nyquist = data.s_freq / 2.

    btype = None
    if low_cut is not None and high_cut is not None:
        if low_cut > nyquist or high_cut > nyquist:
            raise ValueError('cutoff has to be less than Nyquist '
                             'frequency')
        btype = 'bandpass'
        Wn = (low_cut / nyquist,
              high_cut / nyquist)

    elif low_cut is not None:
        if low_cut > nyquist:
            raise ValueError('cutoff has to be less than Nyquist '
                             'frequency')
        btype = 'highpass'
        Wn = low_cut / nyquist

    elif high_cut is not None:
        if high_cut > nyquist:
            raise ValueError('cutoff has to be less than Nyquist '
                             'frequency')
        btype = 'lowpass'
        Wn = high_cut / nyquist

    if not btype:
        raise TypeError('You should specify at least low_cut or high_cut')

    if Rs is None:
        Rs = 40

    lg.debug('order {0: 2}, Wn {1}, btype {2}, ftype {3}'
             ''.format(order, str(Wn), btype, ftype))
    b, a = iirfilter(order, Wn, btype=btype, ftype=ftype, rs=Rs)

    fdata = data._copy()
    for i in range(data.number_of('trial')):
        fdata.data[i] = filtfilt(b, a,
                                 data.data[i],
                                 axis=data.index_of(axis))
    return fdata


def convolve(data, window, axis='time', length=1):
    """Design taper and convolve it with the signal.

    Parameters
    ----------
    data : instance of Data
        the data to filter.
    window : str
        one of the windows in scipy, using get_window
    length : float, optional
        length of the window
    axis : str, optional
        axis to apply the filter on.

    Returns
    -------
    instance of DataRaw
        data after convolution

    Notes
    -----
    Most of the code is identical to fftconvolve(axis=data.index_of(axis))
    but unfortunately fftconvolve in scipy 0.13 doesn't take that argument
    so we need to redefine it here. It's pretty slow too.

    Taper is normalized such that the integral of the function remains the
    same even after convolution.

    See Also
    --------
    scipy.signal.get_window : function used to create windows
    """
    taper = get_window(window, length * data.s_freq)
    taper = taper / sum(taper)

    fdata = data._copy()
    idx_axis = data.index_of(axis)

    for i in range(data.number_of('trial')):
        orig_dat = data.data[i]

        sel_dim = []
        i_dim = []
        dat = empty(orig_dat.shape, dtype=orig_dat.dtype)
        for i_axis, one_axis in enumerate(data.list_of_axes):
            if one_axis != axis:
                i_dim.append(i_axis)
                sel_dim.append(range(data.number_of(one_axis)[i]))

        for one_iter in product(*sel_dim):
            # create the numpy indices for one value per dimension,
            # except for the dimension of interest
            idx = [[x] for x in one_iter]
            idx.insert(idx_axis, range(data.number_of(axis)[i]))
            indices = ix_(*idx)

            d_1dim = squeeze(orig_dat[indices], axis=i_dim)

            d_1dim = fftconvolve(d_1dim, taper, 'same')

            for to_squeeze in i_dim:
                d_1dim = expand_dims(d_1dim, axis=to_squeeze)
                dat[indices] = d_1dim
        fdata.data[0] = dat

    return fdata
