"""Analysis and export convenience functions.
"""

from logging import getLogger
from itertools import compress
from csv import writer
from numpy import (amax, amin, asarray, concatenate, in1d, mean, negative, ptp, 
                   reshape, sqrt, square)

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QProgressDialog
except ImportError:
    Qt = None
    QProgressDialog = None

from .. import __version__
from .math import math, get_descriptives
from .frequency import band_power
from .peaks import get_slopes

lg = getLogger(__name__)


def event_params(segments, params, band=None, n_fft=None, slopes=None, 
                 prep=None, parent=None):
    """Compute event parameters.
    
    Parameters
    ----------
    segments : instance of wonambi.trans.select.Segments
        list of segments, with time series and metadata
    params : dict of bool, or str
        'dur', 'minamp', 'maxamp', 'ptp', 'rms', 'power', 'peakf', 'energy', 
        'peakef'. If 'all', a dict will be created with these keys and all 
        values as True, so that all parameters are returned.
    band : tuple of float
        band of interest for power and energy
    n_fft : int
        length of FFT. if shorter than input signal, signal is truncated; if 
        longer, signal is zero-padded to length
    slopes : dict of bool
        'avg_slope', 'max_slope', 'prep', 'invert'
    prep : dict of bool
        same keys as params. if True, segment['trans_data'] will be used as dat
    parent : QMainWindow
        for use with GUI only
        
    Returns
    -------
    list of dict
        list of segments, with time series, metadata and parameters
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
                                                 scaling=pw, n_fft=n_fft)
                if not (prep[pw] and prep[pk]):
                    raw_pw, raw_pk = band_power(dat, band, 
                                                scaling=pw, n_fft=n_fft)

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
    param_headings_2 = ['Power (uV^2)',
                        'Peak power frequency (Hz)',
                        'Energy (uV^2s)',
                        'Peak energy frequency (Hz)']
    slope_headings =   ['Q1 average slope (uV/s)',
                        'Q2 average slope (uV/s)',
                        'Q3 average slope (uV/s)',
                        'Q4 average slope (uV/s)',
                        'Q23 average slope (uV/s)',
                        'Q1 max. slope (uV/s^2)',
                        'Q2 max. slope (uV/s^2)',
                        'Q3 max. slope (uV/s^2)',
                        'Q4 max. slope (uV/s^2)',
                        'Q23 max. slope (uV/s^2)']
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
        csv_file.writerow(['Wonambi v{}'.format(__version__)])

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

def export_freq(xfreq, filename, desc=None):
    """Write frequency analysis data to CSV.

    Parameters
    ----------
    xfreq : list of dict
        spectral data, one dict per segment, where 'data' is ChanFreq
    filename : str
        output filename
    desc : dict of ndarray
        descriptives
    '"""
    heading_row_1 = ['Segment index',
                   'Start time',
                   'End time',
                   'Duration',
                   'Stitches',
                   'Stage',
                   'Cycle',
                   'Event type',
                   'Channel',
                   ]
    spacer = [''] * (len(heading_row_1) - 1)
    freq = list(xfreq[0]['data'].axis['freq'][0])

    with open(filename, 'w', newline='') as f:
        lg.info('Writing to ' + str(filename))
        csv_file = writer(f)
        csv_file.writerow(['Wonambi v{}'.format(__version__)])
        csv_file.writerow(heading_row_1 + freq)

        if desc:
            csv_file.writerow(['Mean'] + spacer + list(desc['mean']))
            csv_file.writerow(['SD'] + spacer + list(desc['sd']))
            csv_file.writerow(['Mean of ln'] + spacer + list(
                    desc['mean_log']))
            csv_file.writerow(['SD of ln'] + spacer + list(desc['sd_log']))

        idx = 0
        for seg in xfreq:

            for chan in seg['data'].axis['chan'][0]:
                idx += 1

                cyc = None
                if seg['cycle'] is not None:
                    cyc = seg['cycle'][2]

                data_row = list(seg['data'](chan=chan)[0])
                csv_file.writerow([idx,
                                   seg['start'],
                                   seg['end'],
                                   seg['duration'],
                                   seg['n_stitch'],
                                   seg['stage'],
                                   cyc,
                                   seg['name'],
                                   chan,
                                   ] + data_row)


def export_freq_band(xfreq, bands, filename):
    """Write frequency analysis data to CSV by pre-defined band."""
    heading_row_1 = ['Segment index',
                   'Start time',
                   'End time',
                   'Duration',
                   'Stitches',
                   'Stage',
                   'Cycle',
                   'Event type',
                   'Channel',
                   ]
    spacer = [''] * (len(heading_row_1) - 1)
    band_hdr = [str(b1) + '-' + str(b2) for b1, b2 in bands]
    xband = xfreq.copy()

    for seg in xband:
        bandlist = []

        for i, b in enumerate(bands):
            pwr, _ = band_power(seg['data'], b)
            bandlist.append(pwr)

        seg['band'] = bandlist

    as_matrix = asarray([
            [x['band'][y][chan] for y in range(len(x['band']))] \
            for x in xband for chan in x['band'][0].keys()])
    desc = get_descriptives(as_matrix)

    with open(filename, 'w', newline='') as f:
        lg.info('Writing to ' + str(filename))
        csv_file = writer(f)
        csv_file.writerow(['Wonambi v{}'.format(__version__)])
        csv_file.writerow(heading_row_1 + band_hdr)
        csv_file.writerow(['Mean'] + spacer + list(desc['mean']))
        csv_file.writerow(['SD'] + spacer + list(desc['sd']))
        csv_file.writerow(['Mean of ln'] + spacer + list(desc['mean_log']))
        csv_file.writerow(['SD of ln'] + spacer + list(desc['sd_log']))
        idx = 0

        for seg in xband:

            for chan in seg['band'][0].keys():
                idx += 1

                cyc = None
                if seg['cycle'] is not None:
                    cyc = seg['cycle'][2]

                data_row = list(
                        [seg['band'][x][chan] for x in range(
                                len(seg['band']))])
                csv_file.writerow([idx,
                                   seg['start'],
                                   seg['end'],
                                   seg['duration'],
                                   seg['n_stitch'],
                                   seg['stage'],
                                   cyc,
                                   seg['name'],
                                   chan,
                                   ] + data_row)

def _amax(x, axis, keepdims=None):
    return amax(x, axis=axis)

def _amin(x, axis, keepdims=None):
    return amin(x, axis=axis)

def _ptp(x, axis, keepdims=None):
    return ptp(x, axis=axis)

def _mean(x, axis, keepdims=None):
    return mean(x, axis=axis)