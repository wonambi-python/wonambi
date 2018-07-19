"""Convenient module to convert data based on simple mathematical operations.
"""
from inspect import getfullargspec
from logging import getLogger
from itertools import compress
from csv import writer

# for Math
from numpy import (absolute,
                   angle,
                   amax, 
                   amin,
                   asarray,
                   concatenate,
                   diff,
                   empty,
                   exp,
                   gradient,
                   in1d,
                   isinf,
                   log,
                   log10,
                   median,
                   mean,
                   nan,
                   nanmean,
                   nanstd,
                   negative,
                   ones,
                   pad,
                   ptp,
                   reshape,
                   sign,
                   sqrt,
                   square,
                   sum,
                   std,
                   where,
                   unwrap)
from scipy.signal import detrend, hilbert, fftconvolve
from scipy.stats import mode

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressDialog

from . import band_power

lg = getLogger(__name__)

NOKEEPDIM = (median, mode)


def math(data, operator=None, operator_name=None, axis=None):
    """Apply mathematical operation to each trial and channel individually.

    Parameters
    ----------
    data : instance of DataTime, DataFreq, or DataTimeFreq

    operator : function or tuple of functions, optional
        function(s) to run on the data.
    operator_name : str or tuple of str, optional
        name of the function(s) to run on the data.
    axis : str, optional
        for functions that accept it, which axis you should run it on.

    Returns
    -------
    instance of Data
        data where the trials underwent operator.

    Raises
    ------
    TypeError
        If you pass both operator and operator_name.
    ValueError
        When you try to operate on an axis that has already been removed.

    Notes
    -----
    operator and operator_name are mutually exclusive. operator_name is given
    as shortcut for most common operations.

    If a function accepts an 'axis' argument, you need to pass 'axis' to the
    constructor. In this way, it'll apply the function to the correct
    dimension.

    The possible point-wise operator_name are:
    'absolute', 'angle', 'dB' (=10 * log10), 'exp', 'log', 'sqrt', 'square',
    'unwrap'

    The operator_name's that need an axis, but do not remove it:
    'hilbert', 'diff', 'detrend'

    The operator_name's that need an axis and remove it:
    'mean', 'median', 'mode', 'std'

    Examples
    --------
    You can pass a single value or a tuple. The order starts from left to
    right, so abs of the hilbert transform, should be:

    >>> rms = math(data, operator_name=('hilbert', 'abs'), axis='time')

    If you want to pass the power of three, use lambda (or partial):

    >>> p3 = lambda x: power(x, 3)
    >>> data_p3 = math(data, operator=p3)

    Note that lambdas are fine with point-wise operation, but if you want them
    to operate on axis, you need to pass ''axis'' as well, so that:

    >>> std_ddof = lambda x, axis: std(x, axis, ddof=1)
    >>> data_std = math(data, operator=std_ddof)

    If you don't pass 'axis' in lambda, it'll never know on which axis the
    function should be applied and you'll get unpredictable results.

    If you want to pass a function that operates on an axis and removes it (for
    example, if you want the max value over time), you need to add an argument
    in your function called ''keepdims'' (the values won't be used):

    >>> def func(x, axis, keepdims=None):
    >>>     return nanmax(x, axis=axis)
    """
    if operator is not None and operator_name is not None:
        raise TypeError('Parameters "operator" and "operator_name" are '
                        'mutually exclusive')

    # turn input into a tuple of functions in operators
    if operator_name is not None:
        if isinstance(operator_name, str):
            operator_name = (operator_name, )

        operators = []
        for one_operator_name in operator_name:
            operators.append(eval(one_operator_name))
        operator = tuple(operators)

    # make it an iterable
    if callable(operator):
        operator = (operator, )

    operations = []
    for one_operator in operator:
        on_axis = False
        keepdims = True

        try:
            args = getfullargspec(one_operator).args
        except TypeError:
            lg.debug('func ' + str(one_operator) + ' is not a Python '
                     'function')
        else:
            if 'axis' in args:
                on_axis = True

                if axis is None:
                    raise TypeError('You need to specify an axis if you '
                                    'use ' + one_operator.__name__ +
                                    ' (which applies to an axis)')

            if 'keepdims' in args or one_operator in NOKEEPDIM:
                keepdims = False

        operations.append({'name': one_operator.__name__,
                           'func': one_operator,
                           'on_axis': on_axis,
                           'keepdims': keepdims,
                           })

    output = data._copy()

    if axis is not None:
        idx_axis = data.index_of(axis)

    first_op = True
    for op in operations:
        #lg.info('running operator: ' + op['name'])
        func = op['func']

        if func == mode:
            func = lambda x, axis: mode(x, axis=axis)[0]

        for i in range(output.number_of('trial')):

            # don't copy original data, but use data if it's the first operation
            if first_op:
                x = data(trial=i)
            else:
                x = output(trial=i)

            if op['on_axis']:
                lg.debug('running ' + op['name'] + ' on ' + str(idx_axis))

                try:
                    if func == diff:
                        lg.debug('Diff has one-point of zero padding')
                        x = _pad_one_axis_one_value(x, idx_axis)
                    output.data[i] = func(x, axis=idx_axis)

                except IndexError:
                    raise ValueError('The axis ' + axis + ' does not '
                                     'exist in [' +
                                     ', '.join(list(data.axis.keys())) + ']')

            else:
                lg.debug('running ' + op['name'] + ' on each datapoint')
                output.data[i] = func(x)

        first_op = False

        if op['on_axis'] and not op['keepdims']:
            del output.axis[axis]

    return output


def event_params(segments, params, band=None, slopes=None, prep=None,
                 parent=None):
    """Compute event parameters.
    
    Parameters
    ----------
    segments : instance of wonambi.trans.select.Segments
        list of segments, with time series and metadata
    params : dict
    band : tuple of float
        band of interest for power and energy
    slopes : dict
    prep : dict
    parent : 
        """
    if parent is not None:
        progress = QProgressDialog('Computing parameters', 'Abort',
                                   0, len(segments) - 1, parent)
        progress.setWindowModality(Qt.ApplicationModal)

    param_keys = ['dur', 'minamp', 'maxamp', 'ptp', 'rms', 'power', 'peakpf', 
                  'energy', 'peakef']
    
    if params == 'all':
        params = {k: 1 for k in param_keys}
    if prep is None:
        prep = {k: 0 for k in param_keys}    
    if band is None:
        band = (None, None)

    params_out = []
    evt_output = False

    for i, seg in enumerate(segments):
        out = dict(seg)
        dat = seg['data']            

        if params['dur']:
            out['dur'] = float(dat.number_of('time')) / dat.s_freq
            evt_output = True

        if params['minamp']:
            dat1 = dat
            if prep['minamp']:
                dat1 = seg['trans_data']
            out['minamp'] = math(dat1, operator=_amin, axis='time')
            evt_output = True

        if params['maxamp']:
            dat1 = dat
            if prep['maxamp']:
                dat1 = seg['trans_data']
            out['maxamp'] = math(dat1, operator=_amax, axis='time')
            evt_output = True

        if params['ptp']:
            dat1 = dat
            if prep['ptp']:
                dat1 = seg['trans_data']
            out['ptp'] = math(dat1, operator=_ptp, axis='time')
            evt_output = True

        if params['rms']:
            dat1 = dat
            if prep['rms']:
                dat1 = seg['trans_data']
            out['rms'] = math(dat1, operator=(square, _mean, sqrt),
               axis='time')
            evt_output = True

        for pw, pk in [('power', 'peakpf'), ('energy', 'peakef')]:

            if params[pw] or params[pk]:
                evt_output = True

                if prep[pw] or prep[pk]:
                    prep_pw, prep_pk = band_power(seg['trans_data'], band,
                                                 scaling=pw)
                if not (prep[pw] and prep[pk]):
                    raw_pw, raw_pk = band_power(dat, band, scaling=pw)

                if prep[pw]:
                    out[pw] = prep_pw
                else:
                    out[pw] = raw_pw

                if prep[pk]:
                    out[pk] = prep_pk
                else:
                    out[pk] = raw_pk

        if slopes:
            evt_output = True
            out['slope'] = {}
            dat1 = dat
            if slopes['prep']:
                dat1 = seg['trans_data']
            if slopes['invert']:
                dat1 = math(dat1, operator=negative, axis='time')

            if slopes['avg_slope'] and slopes['max_slope']:
                level = 'all'
            elif slopes['avg_slope']:
                level = 'average'
            else:
                level = 'maximum'

            for chan in dat1.axis['chan'][0]:
                d = dat1(chan=chan)[0]
                out['slope'][chan] = get_slopes(d, dat.s_freq, level=level)
                
        if evt_output:
            timeline = dat.axis['time'][0]
            out['start'] = timeline[0]
            out['end'] = timeline[-1]
            params_out.append(out)

        if parent:
            progress.setValue(i)
            if progress.wasCanceled():
                msg = 'Analysis canceled by user.'
                parent.statusBar().showMessage(msg)
                return

    if parent:
        progress.close()

    return params_out

def export_event_params(filename, params, count=None, density=None):
    """Write event analysis data to CSV."""
    heading_row_1 = ['Segment index',
                   'Start time',
                   'End time',
                   'Stitches',
                   'Stage',
                   'Cycle',
                   'Event type',
                   'Channel']
    spacer = [''] * (len(heading_row_1) - 1)

    param_headings_1 = ['Min. amplitude (uV)',
                        'Max. amplitude (uV)',
                        'Peak-to-peak amplitude (uV)',
                        'RMS (uV)']
    param_headings_2 = ['Power (uV**2)',
                        'Peak power frequency (Hz)',
                        'Energy (uV**2/s)',
                        'Peak energy frequency (Hz)']
    slope_headings =   ['Q1 average slope (uV/s)',
                        'Q2 average slope (uV/s)',
                        'Q3 average slope (uV/s)',
                        'Q4 average slope (uV/s)',
                        'Q23 average slope (uV/s)',
                        'Q1 max. slope (uV/s**2)',
                        'Q2 max. slope (uV/s**2)',
                        'Q3 max. slope (uV/s**2)',
                        'Q4 max. slope (uV/s**2)',
                        'Q23 max. slope (uV/s**2)']
    ordered_params_1 = ['minamp', 'maxamp', 'ptp', 'rms']
    ordered_params_2 = ['power', 'peakpf', 'energy', 'peakef']

    idx_params_1 = in1d(ordered_params_1, list(params[0].keys()))
    sel_params_1 = list(compress(ordered_params_1, idx_params_1))
    heading_row_2 = list(compress(param_headings_1, idx_params_1))

    if 'dur' in params[0].keys():
        heading_row_2 = ['Duration (s)'] + heading_row_2

    idx_params_2 = in1d(ordered_params_2, list(params[0].keys()))
    sel_params_2 = list(compress(ordered_params_2, idx_params_2))
    heading_row_3 = list(compress(param_headings_2, idx_params_2))

    heading_row_4 = []
    if 'slope' in params[0].keys():
        if next(iter(params[0]['slope']))[0]:
            heading_row_4.extend(slope_headings[:5])
        if next(iter(params[0]['slope']))[1]:
            heading_row_4.extend(slope_headings[5:])

    # Get data as matrix and compute descriptives
    dat = []
    if 'dur' in params[0].keys():
        one_mat = asarray([seg['dur'] for seg in params \
                           for chan in seg['data'].axis['chan'][0]])
        one_mat = reshape(one_mat, (len(one_mat), 1))
        dat.append(one_mat)

    if sel_params_1:
        one_mat = asarray([[seg[x](chan=chan)[0] for x in sel_params_1] \
                for seg in params for chan in seg['data'].axis['chan'][0]])
        dat.append(one_mat)

    if sel_params_2:
        one_mat = asarray([[seg[x][chan] for x in sel_params_2] \
                for seg in params for chan in seg['data'].axis['chan'][0]])
        dat.append(one_mat)

    if 'slope' in params[0].keys():
        one_mat = asarray([[x for y in seg['slope'][chan] for x in y] \
                for seg in params for chan in seg['data'].axis['chan'][0]])
        dat.append(one_mat)

    if dat:
        dat = concatenate(dat, axis=1)
        desc = get_descriptives(dat)

    with open(filename, 'w', newline='') as f:
        lg.info('Writing to ' + str(filename))
        csv_file = writer(f)

        if count:
            csv_file.writerow(['Count', count])
        if density:
            csv_file.writerow(['Density', density])

        if dat == []:
            return

        csv_file.writerow(heading_row_1 + heading_row_2 + heading_row_3 \
                          + heading_row_4)
        csv_file.writerow(['Mean'] + spacer + list(desc['mean']))
        csv_file.writerow(['SD'] + spacer + list(desc['sd']))
        csv_file.writerow(['Mean of ln'] + spacer + list(desc['mean_log']))
        csv_file.writerow(['SD of ln'] + spacer + list(desc['sd_log']))
        idx = 0

        for seg in params:
            if seg['cycle'] is not None:
                seg['cycle'] = seg['cycle'][2]

            for chan in seg['data'].axis['chan'][0]:
                idx += 1
                data_row_1 = [seg[x](chan=chan)[0] for x in sel_params_1]
                data_row_2 = [seg[x][chan] for x in sel_params_2]

                if 'dur' in seg.keys():
                    data_row_1 = [seg['dur']] + data_row_1

                if 'slope' in seg.keys():
                    data_row_3 = [x for y in seg['slope'][chan] for x in y]
                    data_row_2 = data_row_2 + data_row_3

                csv_file.writerow([idx,
                                   seg['start'],
                                   seg['end'],
                                   seg['n_stitch'],
                                   seg['stage'],
                                   seg['cycle'],
                                   seg['name'],
                                   chan,
                                   ] + data_row_1 + data_row_2)

def get_descriptives(data):
    """Get mean, SD, and mean and SD of log values.

    Parameters
    ----------
    data : ndarray
        Data with segment as first dimension
        and all other dimensions raveled into second dimension.

    Returns
    -------
    dict of ndarray
        each entry is a 1-D vector of descriptives over segment dimension
    """
    output = {}
    dat_log = log(abs(data))
    output['mean'] = nanmean(data, axis=0)
    output['sd'] = nanstd(data, axis=0)
    output['mean_log'] = nanmean(dat_log, axis=0)
    output['sd_log'] = nanstd(dat_log, axis=0)

    return output


def get_slopes(data, s_freq, level='all', smooth=0.05):
    """Get the slopes (average and/or maximum) for each quadrant of a slow
    wave, as well as the combination of quadrants 2 and 3.

    Parameters
    ----------
    data : ndarray
        raw data as vector
    s_freq : int
        sampling frequency
    level : str
        if 'average', returns average slopes (uV / s). if 'maximum', returns
        the maximum of the slope derivative (uV / s**2). if 'all', returns all.
    smooth : float or None
        if not None, signal will be smoothed by moving average, with a window
        of this duration

    Returns
    -------
    tuple of ndarray
        each array is len 5, with q1, q2, q3, q4 and q23. First array is
        average slopes and second is maximum slopes.

    Notes
    -----
    This function is made to take automatically detected start and end
    times AS WELL AS manually delimited ones. In the latter case, the first
    and last zero has to be detected within this function.
    """
    nan_array = empty((5,))
    nan_array[:] = nan
    idx_trough = data.argmin()
    idx_peak = data.argmax()
    if idx_trough >= idx_peak:
        return nan_array, nan_array

    zero_crossings_0 = where(diff(sign(data[:idx_trough])))[0]
    zero_crossings_1 = where(diff(sign(data[idx_trough:idx_peak])))[0]
    zero_crossings_2 = where(diff(sign(data[idx_peak:])))[0]
    if zero_crossings_1.any():
        idx_zero_1 = idx_trough + zero_crossings_1[0]
    else:
        return nan_array, nan_array

    if zero_crossings_0.any():
        idx_zero_0 = zero_crossings_0[-1]
    else:
        idx_zero_0 = 0

    if zero_crossings_2.any():
        idx_zero_2 = idx_peak + zero_crossings_2[0]
    else:
        idx_zero_2 = len(data) - 1

    avgsl = nan_array
    if level in ['average', 'all']:
        q1 = data[idx_trough] / ((idx_trough - idx_zero_0) / s_freq)
        q2 = data[idx_trough] / ((idx_zero_1 - idx_trough) / s_freq)
        q3 = data[idx_peak] / ((idx_peak - idx_zero_1) / s_freq)
        q4 = data[idx_peak] / ((idx_zero_2 - idx_peak) / s_freq)
        q23 = (data[idx_peak] - data[idx_trough]) \
                / ((idx_peak - idx_trough) / s_freq)
        avgsl = asarray([q1, q2, q3, q4, q23])
        avgsl[isinf(avgsl)] = nan

    maxsl = nan_array
    if level in ['maximum', 'all']:

        if smooth is not None:
            win = int(smooth * s_freq)
            flat = ones(win)
            data = fftconvolve(data, flat / sum(flat), mode='same')

        if idx_trough - idx_zero_0 >= win:
            maxsl[0] = min(gradient(data[idx_zero_0:idx_trough]))

        if idx_zero_1 - idx_trough >= win:
            maxsl[1] = max(gradient(data[idx_trough:idx_zero_1]))

        if idx_peak - idx_zero_1 >= win:
            maxsl[2] = max(gradient(data[idx_zero_1:idx_peak]))

        if idx_zero_2 - idx_peak >= win:
            maxsl[3] = min(gradient(data[idx_peak:idx_zero_2]))

        if idx_peak - idx_trough >= win:
            maxsl[4] = max(gradient(data[idx_trough:idx_peak]))

        maxsl[isinf(maxsl)] = nan

    return avgsl, maxsl


def _pad_one_axis_one_value(x, idx_axis):
    pad_width = [(0, 0)] * x.ndim
    pad_width[idx_axis] = (1, 0)
    return pad(x, pad_width=pad_width, mode='mean')


# additional operators
def dB(x):
    return 10 * log10(x)

def _amax(x, axis, keepdims=None):
    return amax(x, axis=axis)

def _amin(x, axis, keepdims=None):
    return amin(x, axis=axis)

def _ptp(x, axis, keepdims=None):
    return ptp(x, axis=axis)

def _mean(x, axis, keepdims=None):
    return mean(x, axis=axis)
