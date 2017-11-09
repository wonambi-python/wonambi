"""Module to select periods of interest, based on number of trials or any of
the axes.

There is some overlap between Select and the Data.__call__(). The main
difference is that Select takes an instance of Data as input and returns
another instance of Data as output, whil Data.__call__() returns the actual
content of the data.

Select should be as flexible as possible. There are quite a few cases, which
will be added as we need them.
"""
from collections import Iterable
from logging import getLogger

from numpy import asarray, empty, linspace, ones, setdiff1d
from numpy.lib.stride_tricks import as_strided
from scipy.signal import decimate

lg = getLogger(__name__)


def select(data, trial=None, invert=False, **axes_to_select):
    """Define the selection of trials, using ranges or actual values.

    Parameters
    ----------
    data : instance of Data
        data to select from.
    trial : list of int or ndarray (dtype='i'), optional
        index of trials of interest
    **axes_to_select, optional
        Values need to be tuple or list. If the values in one axis are string,
        then you need to specify all the strings that you want. If the values
        are numeric, then you should specify the range (you cannot specify
        single values, nor multiple values). To select only up to one point,
        you can use (None, value_of_interest)
    invert : bool
        take the opposite selection

    Returns
    -------
    instance, same class as input
        data where selection has been applied.
    """
    if trial is not None and not isinstance(trial, Iterable):
        raise TypeError('Trial needs to be iterable.')

    for axis_to_select, values_to_select in axes_to_select.items():
        if (not isinstance(values_to_select, Iterable) or
           isinstance(values_to_select, str)):
            raise TypeError(axis_to_select + ' needs to be iterable.')

    if trial is None:
        trial = range(data.number_of('trial'))
    else:
        trial = trial
        if invert:
            trial = setdiff1d(range(data.number_of('trial')), trial)

    # create empty axis
    output = data._copy(axis=False)
    for one_axis in output.axis:
        output.axis[one_axis] = empty(len(trial), dtype='O')
    output.data = empty(len(trial), dtype='O')

    to_select = {}
    for cnt, i in enumerate(trial):
        lg.debug('Selection on trial {0: 6}'.format(i))
        for one_axis in output.axis:
            values = data.axis[one_axis][i]

            if one_axis in axes_to_select.keys():
                values_to_select = axes_to_select[one_axis]

                if len(values_to_select) == 0:
                    selected_values = ()

                elif isinstance(values_to_select[0], str):
                    selected_values = asarray(values_to_select, dtype='U')

                else:
                    if (values_to_select[0] is None and
                       values_to_select[1] is None):
                        bool_values = ones(len(values), dtype=bool)
                    elif values_to_select[0] is None:
                        bool_values = values < values_to_select[1]
                    elif values_to_select[1] is None:
                        bool_values = values_to_select[0] <= values
                    else:
                        bool_values = ((values_to_select[0] <= values) &
                                       (values < values_to_select[1]))
                    selected_values = values[bool_values]

                if invert:
                    selected_values = setdiff1d(values, selected_values)

                lg.debug('In axis {0}, selecting {1: 6} '
                         'values'.format(one_axis,
                                         len(selected_values)))
                to_select[one_axis] = selected_values
            else:
                lg.debug('In axis ' + one_axis + ', selecting all the '
                         'values')
                selected_values = data.axis[one_axis][i]

            output.axis[one_axis][cnt] = selected_values

        output.data[cnt] = data(trial=i, **to_select)

    return output


def resample(data, s_freq=None, axis='time', ftype='fir', n=None):
    """Downsample the data after applying a filter.

    Parameters
    ----------
    data : instance of Data
        data to downsample
    s_freq : int or float
        desired sampling frequency
    axis : str
        axis you want to apply downsample on (most likely 'time')
    ftype : str
        filter type to apply. The default here is 'fir', like Matlab but unlike
        the default in scipy, because it works better
    n : int
        The order of the filter (1 less than the length for ‘fir’).

    Returns
    -------
    instance of Data
        downsampled data
    """
    output = data._copy()
    ratio = int(data.s_freq / s_freq)

    for i in range(data.number_of('trial')):
        output.data[i] = decimate(data.data[i], ratio,
                                  axis=data.index_of(axis),
                                  zero_phase=True)

        n_samples = output.data[i].shape[data.index_of(axis)]
        output.axis[axis][i] = linspace(data.axis[axis][i][0],
                                        data.axis[axis][i][-1] +
                                        1 / data.s_freq,
                                        n_samples)

    output.s_freq = s_freq

    return output


def _create_subepochs(x, nperseg, step):
    """Transform the data into a matrix for easy manipulation
    
    Parameters
    ----------
    x : 1d ndarray
        actual data values
    nperseg : int
        number of samples in each row to create
    step : int
        distance in samples between rows
    Returns
    -------
    2d ndarray
        a view (i.e. doesn't copy data) of the original x, with shape
        determined by nperseg and step. You should use the last dimension
    """
    axis = x.ndim - 1  # last dim
    nsmp = x.shape[axis]
    stride = x.strides[axis]
    noverlap = nperseg - step
    v_shape = *x.shape[:axis], (nsmp - noverlap) // step, nperseg
    v_strides = *x.strides[:axis], stride * step, stride
    v = as_strided(x, shape=v_shape, strides=v_strides,
                  writeable=False)  # much safer
    return v