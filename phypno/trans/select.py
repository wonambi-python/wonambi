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

from numpy import asarray, empty, where


def _select_time(output, time):
    """Select time window for each trial.

    Parameters
    ----------
    output : instance of phypno.DataTime

    time : tuple of 2 float
        which periods you want.

    Returns
    -------
    instance of phypno.DataTime
        where only the time window of interest is selected.

    Notes
    -----
    Some trials might be empty.

    """
    for i in range(len(output.data)):
        begsam = int(where(output.time[i] >= time[0])[0][0])
        endsam = int(where(output.time[i] >= time[1])[0][0])
        lg.info('Trial {0: 3}: selecting {1: 3}-{2: 3} time, while data '
                ' is between {3: 3}-{4: 3}'.format(i,
                                                   time[0], time[1],
                                                   output.time[0][0],
                                                   output.time[0][-1]))
        lg.debug('Selecting first sample {0: 5} and last sample '
                 '{1: 5}'.format(begsam, endsam))

        output.time[i] = output.time[i][begsam:endsam]
        output.data[i] = output.data[i][:, begsam:endsam, ...]
    return output


class Select:
    """Define the selection of trials, using ranges or actual values.

    Parameters
    ----------
    trial : list of int or ndarray (dtype='i'), optional
        index of trials of interest
    **axis, optional
        Values need to be tuple, list or ndarray. It does not accept single
        values.

    Notes
    -----
    It only handles axes that have str.

    """
    def __init__(self, trial=None, **axes):

        if trial is not None and not isinstance(trial, Iterable):
            raise TypeError('Trial needs to be iterable.')

        for axis, value in axes.items():
            if not isinstance(value, Iterable) or isinstance(value, str):
                raise TypeError(axis + ' needs to be iterable.')

        self.trial = trial
        self.axis = axes

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
        output = deepcopy(data)

        if self.trial is None:
            self.trial = range(output.number_of('trial'))

        trials_to_keep = []  # TODO: how to do this?

        for axis, values in output.axis:

            output.axis[axis] = empty(len(self.trial), dtype='O')

            cnt = 0
            for i in self.trial:
                if axis in self.axis.items():
                    selected_value = self.axis[axis]

                    if isinstance(selected_value[0], str):
                        output.axis[axis][cnt] = asarray(selected_value,
                                                         dtype='U')
                    else:
                        bool_values = ((selected_value[0] < values[i]) &
                                         (values[i] < selected_value[1]))
                        if not any(bool_values):
                            continue
                        chosen_values = values[bool_values]

                        output.axis[axis][cnt] = asarray(chosen_values,
                                                         dtype=values.dtype)

                else:
                    output.axis[axis][cnt] = data.axis[axis][i]

            cnt += 1 # best to loop over trials, and then axis
        output.data = data(trial=self.trial, **self.axis)

        return output

