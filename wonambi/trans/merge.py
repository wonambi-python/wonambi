"""Module to merge Data together, along different axis and time points.

It does not merge two instances of Data together (TODO).
"""
from logging import getLogger

from numpy import asarray, empty, expand_dims, unique
from numpy import concatenate as cat

from .. import ChanFreq

lg = getLogger(__name__)


def concatenate(data, axis):
    """Concatenate multiple trials into one trials, according to any dimension.

    Parameters
    ----------
    data : instance of DataTime, DataFreq, or DataTimeFreq

    axis : str
        axis that you want to concatenate (it can be 'trial')

    Returns
    -------
    instace of same class as input
        the data will always have only one trial

    Notes
    -----
    If axis is 'trial', it will add one more dimension, and concatenate based
    on it. It will then create a new axis, called 'trial_axis' (not 'trial'
    because that axis is hard-coded).

    If you want to concatenate across trials, you need:

    >>> expand_dims(data1.data[0], axis=1).shape
    """
    output = data._copy(axis=False)

    for dataaxis in data.axis:
        output.axis[dataaxis] = empty(1, dtype='O')

        if dataaxis == axis:
            output.axis[dataaxis][0] = cat(data.axis[dataaxis])
        else:
            output.axis[dataaxis][0] = data.axis[dataaxis][0]

        if len(unique(output.axis[dataaxis][0])) != len(output.axis[dataaxis][0]):
            lg.warning('Axis ' + dataaxis + ' does not have unique values')

    output.data = empty(1, dtype='O')
    if axis == 'trial':

        # create new axis
        new_axis = empty(1, dtype='O')
        n_trial = data.number_of('trial')
        trial_name = ['trial{0:06}'.format(x) for x in range(n_trial)]
        new_axis[0] = asarray(trial_name, dtype='U')
        output.axis['trial_axis'] = new_axis

        # concatenate along the extra dimension
        all_trial = []
        for one_trial in data.data:
            all_trial.append(expand_dims(one_trial, -1))
        output.data[0] = cat(all_trial, axis=-1)

    else:
        output.data[0] = cat(data.data, axis=output.index_of(axis))

    return output

def _merge_metadata(first, second, link='_&_', reverse=False):
    """Take two data dicts and combine their metadata into new dict, in order.
    Alternatively, create new dictionary with combined channels.
    
    Parameters
    ----------
    first : dict or str
        'data' is instance of ChanFreq with only one chan, other values are str
        or can be converted to str
        if str, channel name to be concatenated with second channel in new dict
    second : dict or str
        if dict, same format as 'first'. the metadata for this one will appear 
        second in each new str
        if str, channel name to be concatenated with first channel in new dict
    link : str
        string that links both metadata strings in new metadata
    reverse : bool
        if True, second comes before first in concatenations
        
    Returns
    -------
    dict
        same format as 'first' and 'second', but with metadata concatenated
    """
    dat = ChanFreq()
    dat.data = empty(1, dtype='O')
    dat.data[0] = empty((1, first['data'].number_of('freq')[0]), dtype='f')
    dat.axis['freq'] = empty(1, dtype='O')
    dat.axis['freq'][0] = first['data'].axis['freq'][0]
    dat.axis['chan'] = empty(1, dtype='O')
    
    newdict = dict(first)
    newdict['data'] = dat    
    
    if isinstance(second, str):
        chan1 = first['data'].axis['chan'][0][0]
        newchan = chan1 + link + second
        newdict['data'].axis['chan'][0] = [newchan]
        
        return newdict
    
    for k, v in first.items():
        
        if k == 'data':
            continue
        
        if v != second[k]:
            newdict[k] = str(v) + link + str(second[k])
            lg.info('added ' + str(v) + link + str(second[k]))
            
    return newdict
 