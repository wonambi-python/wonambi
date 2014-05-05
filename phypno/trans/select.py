"""Module to select periods of interest, based on number of trials or any of
the axes.

There is some overlap between Select and the Data.__call__(). The main
difference is that Select takes an instance of Data as input and returns
another instance of Data as output, whil Data.__call__() returns the actual
content of the data.

Select should be as flexible as possible. There are quite a few cases, which
will be added as we need them.

"""
from logging import getLogger
lg = getLogger('phypno')

from collections import Iterable
from copy import deepcopy

from numpy import asarray, empty, linspace
from scipy.signal import resample


class Select:
    """Define the selection of trials, using ranges or actual values.

    Parameters
    ----------
    trial : list of int or ndarray (dtype='i'), optional
        index of trials of interest
    **axes_to_select, optional
        Values need to be tuple or list. If the values in one axis are string,
        then you need to specify all the strings that you want. If the values
        are numeric, then you should specify the range (you cannot specify
        single values, nor multiple values).

    """
    def __init__(self, trial=None, **axes_to_select):

        if trial is not None and not isinstance(trial, Iterable):
            raise TypeError('Trial needs to be iterable.')

        for axis_to_select, values_to_select in axes_to_select.items():
            if (not isinstance(values_to_select, Iterable) or
                isinstance(values_to_select, str)):
                raise TypeError(axis_to_select + ' needs to be iterable.')

        self.trial = trial
        self.axis_to_select = axes_to_select

    def __call__(self, data):
        """Apply selection to the data.

        Parameters
        ----------
        data : instance of Data
            data to select from.

        Returns
        -------
        instance, same class as input
            data where selection has been applied.

        """
        if self.trial is None:
            self.trial = range(data.number_of('trial'))

        # create empty axis
        output = deepcopy(data)
        for one_axis in output.axis:
            output.axis[one_axis] = empty(len(self.trial), dtype='O')
        output.data = empty(len(self.trial), dtype='O')

        to_select = {}
        for cnt, i in enumerate(self.trial):
            lg.debug('Selection on trial {0: 6}'.format(i))
            for one_axis in output.axis:
                values = data.axis[one_axis][i]

                if one_axis in self.axis_to_select.keys():
                    values_to_select = self.axis_to_select[one_axis]

                    if len(values_to_select) == 0:
                        selected_values = ()

                    elif isinstance(values_to_select[0], str):
                        selected_values = asarray(values_to_select,
                                                             dtype='U')

                    else:
                        bool_values = ((values_to_select[0] <= values) &
                                       (values < values_to_select[1]))
                        selected_values = values[bool_values]

                    lg.debug('In axis {0}, selecting {1: 6} '
                             'values'.format(one_axis,
                                             len(selected_values)))

                else:
                    lg.debug('In axis ' + one_axis + ', selecting all the '
                             'values')
                    selected_values = data.axis[one_axis][i]

                output.axis[one_axis][cnt] = selected_values
                to_select[one_axis] = selected_values

            output.data[cnt] = data(trial=i, **to_select)

        return output


class Resample:

    def __init__(self, s_freq=None, axis='time'):
        self.s_freq = s_freq
        self.axis = axis

    def __call__(self, data):
        axis = self.axis

        data = deepcopy(data)

        for i in range(data.number_of('trial')):

            ratio = data.s_freq / self.s_freq
            n_samples = data.axis[axis][i].shape[0] / ratio
            data.axis[axis][i] = linspace(data.axis[axis][i][0],
                                          data.axis[axis][i][-1] +
                                          1 / data.s_freq,
                                          n_samples)

            data.data[i] = resample(data.data[i], n_samples,
                                    axis=data.index_of(axis))
            data.s_freq = self.s_freq

        return data
