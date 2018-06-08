from logging import getLogger

from numpy import (asarray,
                   c_,
                   dot,
                   mean,
                   moveaxis,
                   where,
                   zeros,
                   )
from numpy.linalg import norm, lstsq

from ..attr import Channels

lg = getLogger(__name__)


def montage(data, ref_chan=None, ref_to_avg=False, bipolar=None,
            method='average'):
    """Apply linear transformation to the channels.

    Parameters
    ----------
    data : instance of DataRaw
        the data to filter
    ref_chan : list of str
        list of channels used as reference
    ref_to_avg : bool
        if re-reference to average or not
    bipolar : float
        distance in mm to consider two channels as neighbors and then compute
        the bipolar montage between them.
    method : str
        'average' or 'regression'. 'average' takes the
        average across the channels selected as reference (it can be all) and
        subtract it from each channel. 'regression' keeps the residuals after
        regressing out the mean across channels.

    Returns
    -------
    filtered_data : instance of DataRaw
        filtered data

    Notes
    -----
    If you don't change anything, it returns the same instance of data.
    """
    if ref_to_avg and ref_chan is not None:
        raise TypeError('You cannot specify reference to the average and '
                        'the channels to use as reference')

    if ref_chan is not None:
        if (not isinstance(ref_chan, (list, tuple)) or
            not all(isinstance(x, str) for x in ref_chan)):
                raise TypeError('chan should be a list of strings')

    if ref_chan is None:
        ref_chan = []  # TODO: check bool for ref_chan

    if bipolar:
        if not data.attr['chan']:
            raise ValueError('Data should have Chan information in attr')

        _assert_equal_channels(data.axis['chan'])
        chan_in_data = data.axis['chan'][0]
        chan = data.attr['chan']
        chan = chan(lambda x: x.label in chan_in_data)
        chan, trans = create_bipolar_chan(chan, bipolar)
        data.attr['chan'] = chan

    if ref_to_avg or ref_chan or bipolar:
        mdata = data._copy()

        idx_chan = mdata.index_of('chan')

        for i in range(mdata.number_of('trial')):
            if ref_to_avg or ref_chan:
                if ref_to_avg:
                    ref_chan = data.axis['chan'][i]

                ref_data = data(trial=i, chan=ref_chan)
                if method == 'average':
                    mdata.data[i] = (data(trial=i) - mean(ref_data, axis=idx_chan))
                elif method == 'regression':
                    mdata.data[i] = compute_average_regress(data(trial=i), idx_chan)

            elif bipolar:

                if not data.index_of('chan') == 0:
                    raise ValueError('For matrix multiplication to work, '
                                     'the first dimension should be chan')
                mdata.data[i] = dot(trans, data(trial=i))
                mdata.axis['chan'][i] = asarray(chan.return_label(),
                                                dtype='U')

    else:
        mdata = data

    return mdata


def _assert_equal_channels(axis):
    """check that all the trials have the same channels, in the same order.

    Parameters
    ----------
    axis : ndarray of ndarray
        one of the data axis

    Raises
    ------

    """
    for i0 in axis:
        for i1 in axis:
            if not all(i0 == i1):
                raise ValueError('The channels for all the trials should have '
                                 'the same labels, in the same order.')


def create_bipolar_chan(chan, max_dist):
    chan_dist = zeros((chan.n_chan, chan.n_chan), dtype='bool')
    for i0, chan0 in enumerate(chan.chan):
        for i1, chan1 in enumerate(chan.chan):
            if i0 < i1 and norm(chan0.xyz - chan1.xyz) < max_dist:
                chan_dist[i0, i1] = True

    x_all, y_all = where(chan_dist)

    bipolar_labels = []
    bipolar_xyz = []
    bipolar_trans = []

    for x0, x1 in zip(x_all, y_all):

        new_label = chan.chan[x0].label + '-' + chan.chan[x1].label
        bipolar_labels.append(new_label)

        xyz = mean(c_[chan.chan[x0].xyz, chan.chan[x1].xyz], axis=1)
        bipolar_xyz.append(xyz)

        trans = zeros(chan.n_chan)
        trans[x0] = 1
        trans[x1] = -1
        bipolar_trans.append(trans)

    bipolar_xyz = c_[bipolar_xyz]
    bipolar_trans = c_[bipolar_trans]

    bipolar = Channels(bipolar_labels, bipolar_xyz)

    return bipolar, bipolar_trans


def compute_average_regress(x, idx_chan):
    """Take the mean across channels and regress out the mean from each channel

    Parameters
    ----------
    x : ndarray
        2d array with channels on one dimension
    idx_chan:
        which axis contains channels

    Returns
    -------
    ndarray
        same as x, but with the mean being regressed out
    """
    if x.ndim != 2:
        raise ValueError(f'The number of dimensions must be 2, not {x.ndim}')

    x = moveaxis(x, idx_chan, 0)  # move axis to the front
    avg = mean(x, axis=0)

    x_o = []
    for i in range(x.shape[0]):
        r = lstsq(avg[:, None], x[i, :][:, None], rcond=0)[0]
        x_o.append(
            x[i, :] - r[0, 0] * avg
            )
    return moveaxis(asarray(x_o), 0, idx_chan)
