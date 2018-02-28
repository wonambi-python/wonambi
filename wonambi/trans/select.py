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

from numpy import arange, asarray, empty, inf, linspace, ones, setdiff1d
from numpy.lib.stride_tricks import as_strided
from math import isclose
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


def _select_channels(data, channels):
    """Select channels.

    Parameters
    ----------
    data : instance of ChanTime
        data with all the channels
    channels : list
        channels of interest

    Returns
    -------
    instance of ChanTime
        data with only channels of interest

    Notes
    -----
    This function does the same as sleepytimes.trans.select, but it's much faster.
    sleepytimes.trans.Select needs to flexible for any data type, here we assume
    that we have one trial, and that channel is the first dimension.

    """
    output = data._copy()
    chan_list = list(data.axis['chan'][0])
    idx_chan = [chan_list.index(i_chan) for i_chan in channels]
    output.data[0] = data.data[0][idx_chan, :]
    output.axis['chan'][0] = asarray(channels)

    return output


def get_times(annot, evt_type=None, stage=None, cycle=None, chan=None,
              exclude=True):
    """Get start and end times for selected segments of data, bundled
    together with info.

    Parameters
    ----------
    annot: instance of Annotations
        The annotation file containing events and epochs
    evt_type: list of str, optional
        Enter a list of event types to get events; otherwise, epochs will
        be returned.
    stage: list of str, optional
        Stage(s) of interest. If None, stage is ignored.
    cycle: list of tuple of two float, optional
        Cycle(s) of interest, as start and end times in seconds from record
        start. If None, cycles are ignored.
    chan: list of str or tuple of None
        Channel(s) of interest, only used for events (epochs have no
        channel). Channel format is 'chan_name (group_name)'.
        If None, channel is ignored.
    exclude: bool
        Exclude epochs by quality. If True, epochs marked as 'Poor' quality
        or staged as 'Artefact' will be rejected (and the signal segmented
        in consequence). Has no effect on event selection. Defaults to True.

    Returns
    -------
    list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), stage, cycle, chan, name (event type,
        if applicable)

    Notes
    -----
    This function returns epoch or event start and end times, bundled
    together according to the specified parameters.
    Presently, setting exclude to True does not exclude events found in Poor
    signal epochs. The rationale is that events would never be marked in Poor
    signal epochs. If they were automatically detected, these epochs would
    have been left out during detection. If they were manually marked, then
    it must have been Good signal. At the moment, in the GUI, the exclude epoch
    option is disabled when analyzing events, but we could fix the code if we
    find a use case for rejecting events based on the quality of the epoch
    signal.
    """
    getter = annot.get_epochs

    if stage is None:
        stage = (None,)
    if cycle is None:
        cycle = (None,)
    if chan is None:
        chan = (None,)
    if evt_type is None:
        evt_type = (None,)
    elif isinstance(evt_type[0], str):
        getter = annot.get_events
    else:
        lg.error('Event type must be list/tuple of str or None')

    qual = None
    if exclude:
        qual = 'Good'

    bundles = []
    for et in evt_type:

        for ch in chan:

            for cyc in cycle:

                for ss in stage:

                    st_input = ss
                    if ss is not None:
                        st_input = (ss,)

                    evochs = getter(name=et, time=cyc, chan=(ch,),
                                    stage=st_input, qual=qual)
                    if evochs:
                        times = [(e['start'], e['end']) for e in evochs]
                        times = sorted(times, key=lambda x: x[0])
                        one_bundle = {'times': times,
                                      'stage': ss,
                                      'cycle': cyc,
                                      'chan': ch,
                                      'name': et}
                        bundles.append(one_bundle)

    return bundles


def longer_than(segments, min_dur):
    """
    Parameters
    ----------
    segments : list of dict
        Each dict has times (the start and end times of each sub-segment, as
        list of tuple of float), and the stage, cycle, chan and name (event
        type, if applicable) associated with the segment
    min_dur: float
        Minimum duration of signal chunks returned.
    """
    if min_dur <= 0.:
        return segments

    long_enough = []
    for seg in segments:

        if sum([t[1] - t[0] for t in seg['times']]) >= min_dur:
            long_enough.append(seg)

    return long_enough


def _concat(bundles, cat=(0, 0, 0, 0)):
    """Prepare events or epochs for concatenation.

    Parameters
    ----------
    bundles : list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), and the stage, cycle, chan and name (event
        type, if applicable) associated with the segment bundle
    cat : tuple of int
        Determines whether and where the signal is concatenated.
        If 1st digit is 1, cycles selected in cycle will be
        concatenated.
        If 2nd digit is 1, different stages selected in stage will be
        concatenated.
        If 3rd digit is 1, discontinuous signal within a same condition
        (stage, cycle, event type) will be concatenated.
        If 4th digit is 1, events of different types will be concatenated.
        0 in any position indicates no concatenation.
        Defaults to (0, 0 , 1, 0), i.e. concatenate signal within stages
        only.

    Returns
    -------
    list of dict
        Each dict has times (the start and end times of each subsegment, as
        list of tuple of float), stage, cycle, as well as chan and event
        type name (empty for epochs). Each bundle comprises a collection of
        subsegments to be concatenated.

    TO-DO
    -----
    Make sure the cat options are orthogonal and make sense
    """
    chan = sorted(set([x['chan'] for x in bundles]))
    cycle = sorted(set([x['cycle'] for x in bundles]))
    stage = sorted(set([x['stage'] for x in bundles]))
    evt_type = sorted(set([x['name'] for x in bundles]))

    all_cycle = None
    all_stage = None
    all_evt_type = None

    if cycle[0] is not None:
        all_cycle = ', '.join([str(c) for c in cycle])
    if stage[0] is not None:
        all_stage = ', '.join(stage)
    if evt_type[0] is not None:
        all_evt_type = ', '.join(evt_type)

    if cat[0]:
        cycle = [all_cycle]

    if cat[1]:
        stage = [all_stage]

    if cat[3]:
        evt_type = [all_evt_type]

    lg.info('Concat ' +  ' ,'.join((str(chan), str(cycle), str(stage), str(evt_type))))

    to_concat = []
    for ch in chan:

        for cyc in cycle:

            for st in stage:

                for et in evt_type:
                    new_times = []

                    for bund in bundles:
                        chan_cond = ch == bund['chan']
                        cyc_cond = cyc in (bund['cycle'], all_cycle)
                        st_cond = st in (bund['stage'], all_stage)
                        et_cond = et in (bund['name'], all_evt_type)

                        if chan_cond and cyc_cond and st_cond and et_cond:
                            new_times.extend(bund['times'])

                    new_times = sorted(new_times, key=lambda x: x[0])
                    new_bund = {'times': new_times,
                              'chan': ch,
                              'cycle': cyc,
                              'stage': st,
                              'name': et
                              }
                    to_concat.append(new_bund)

    if not cat[2]:
        to_concat_new = []

        for bund in to_concat:
            last = None
            bund['times'].append((inf,inf))
            start = 0

            for i, j in enumerate(bund['times']):

                if last is not None:
                    if not isclose(j[0], last, abs_tol=0.1):
                        new_times = bund['times'][start:i]
                        new_bund = bund.copy()
                        new_bund['times'] = new_times
                        to_concat_new.append(new_bund)
                        start = i
                last = j[1]

        to_concat = to_concat_new

    to_concat = [x for x in to_concat if x['times']]

    return to_concat


def divide_bundles(bundles):
    """Take each subsegment inside a bundle and put it in its own bundle,
    copying the bundle metadata.

    Parameters
    ----------
    bundles : list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), and the stage, cycle, (chan and name (event
        type, if applicable) associated with the segment bundle.

    Returns
    -------
    list of one dict
        Dict represents a single segment, and has start and end times (tuple
        of float), stage, cycle, chan and name (event type, if applicable)
    """
    divided = []

    for bund in bundles:
        for t in bund['times']:
            new_bund = bund.copy()
            new_bund['times'] = [t]
            divided.append(new_bund)

    return divided


def find_intervals(bundles, interval):
    """Divide bundles into consecutive segments of a certain duration,
    discarding any remainder.

    Parameters
    ----------
    bundles : list of dict
        Each dict has times (the start and end times of each segment, as
        list of tuple of float), and the stage, cycle, (chan and name (event
        type, if applicable) associated with the segment bundle.
        NOTE: Discontinuous segments must already be in separate dicts.
    interval: float
        Duration of consecutive intervals.

    Returns
    -------
    list of dict
        Each dict represents a  segment of duration 'interval', and
        has start and end times (tuple of float), stage, cycle, chan and name
        (event type, if applicable) associated with the single segment.
    """
    segments = []
    for bund in bundles:
        beg, end = bund['times'][0][0], bund['times'][-1][1]

        if end - beg >= interval:
            new_begs = arange(beg, end, interval)[:-1]

            for t in new_begs:
                seg = bund.copy()
                seg['times'] = (t, t + interval)
                segments.append(seg)

    return segments
