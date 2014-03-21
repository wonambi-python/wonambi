"""Module to merge Data together, along different axis and time points.

It does not merge two instances of Data together (TODO).

"""
from logging import getLogger
lg = getLogger('phypno')

from copy import deepcopy

from numpy import asarray, concatenate, empty, expand_dims, unique


class Merge:
    """Merge multiple trials into one trials, according to any dimension.

    Parameters
    ----------
    axis : str
        axis that you want to merge (it can be 'trial')

    Notes
    -----
    If axis is 'trial', it will add one more dimension, and concatenate based
    on it. It will then create a new axis, called 'trial_axis' (not 'trial'
    because that axis is hard-code).

    """
    def __init__(self, axis):
        self.axis = axis

    def __call__(self, data):
        """Merge the data across trials.

        # if you want to concatenate across trials, you need:
        #   expand_dims(data1.data[0], axis=1).shape


        Returns
        -------
        instace of same class as input
            the data will always have only one trial

        """
        output = deepcopy(data)

        for axis in output.axis:
            output.axis[axis] = empty(1, dtype='O')

            if axis == self.axis:
                output.axis[axis][0] = concatenate(data.axis[axis])
            else:
                output.axis[axis][0] = data.axis[axis][0]

            if len(unique(output.axis[axis][0])) != len(output.axis[axis][0]):
                lg.warning('Axis ' + axis + ' does not have unique values')

        output.data = empty(1, dtype='O')
        if self.axis == 'trial':

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
            output.data[0] = concatenate(all_trial, axis=-1)

        else:
            output.data[0] = concatenate(data.data,
                                         axis=output.index_of(self.axis))

        return output
