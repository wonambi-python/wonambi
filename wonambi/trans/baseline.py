from logging import getLogger
from numpy import expand_dims, log10

from .select import select
from .math import math


lg = getLogger(__name__)


def apply_baseline(data, baseline='ratio', **axis_to_select):
    """Apply baseline correction to ChanTime or ChanFreqTime data.

    Parameters
    ----------
    data : instance of ChanTime or ChanFreqTime or ChanFreq
        one of the datatypes
    baseline : str
        type of baseline to apply. One of 'diff', 'ratio', 'dB', 'relchange',
        'percent', 'normchange', 'zscore'
    axis_to_select:  dict
        Specify the subset of data to use as baseline. Examples are:
        "time=(-0.3, -0.1)" or "freq=(50, 60)"
        You can specify only one dimension at the time. Values will be passed
        to wonambi.trans.select.select

    Returns
    -------
    instance, same class as input
        data where baseline has been applied.

    Notes
    -----
    The values of baseline can be (where bl_mean is the mean of the baseline
    selection and bl_std is the standard deviation of the baseline selection):
    - diff : data - bl_mean
    - ratio : data / bl_mean
    - relchange : (data - bl_mean) / bl_mean
    - percent : 100 * (data - bl_mean) / bl_mean
    - normchange : (data - bl_mean) / (data + bl_mean)
    - zscore : (data - bl_mean) / bl_std

    Note that 'dB' uses the geometric mean instead of the arithmetic mean,
    so that the arithmetic mean of the baseline period is then 0
    - dB : 10 * log10 (data / bl_mean)

    For this reason, you should not take the logarithm of the 'ratio', but use
    'dB' instead.

    Furthermore, 'dB' and 'normchange' are only meaningful for positive-only
    data. dB will return NaN for negative values and normchange will return
    incorrect values.
    """
    axis = list(axis_to_select)[0]
    bl_data = select(data, **axis_to_select)
    if baseline in ('dB', ):
        bl_m = math(bl_data, operator_name='gmean', axis=axis)
    else:
        bl_m = math(bl_data, operator_name='mean', axis=axis)
    bl_sd = math(bl_data, operator_name='std', axis=axis)

    out = data._copy()

    for i in range(data.number_of('trial')):

        if baseline in ('diff', 'zscore', 'relchange', 'percent', 'normchange'):
            m = expand_dims(bl_m.data[i], axis=data.index_of(axis))
            out.data[i] = data.data[i] - m

            if baseline in ('relchange', 'percent'):
                out.data[i] /= m

                if baseline == 'percent':
                    out.data[i] *= 100

            elif baseline == 'normchange':
                out.data[i] /= (data.data[i] + m)

            elif baseline == 'zscore':
                sd = expand_dims(bl_sd.data[i], axis=data.index_of(axis))
                out.data[i] /= sd

        elif baseline in ('ratio', 'dB'):
            m = expand_dims(bl_m.data[i], axis=data.index_of(axis))

            out.data[i] = data.data[i] / m

            if baseline == 'dB':
                if not (out.data[i] >= 0).all():
                    lg.warning('Some of the values are negative. It does not make sense to compute dB')

                out.data[i] = 10 * log10(out.data[i])

    return out
