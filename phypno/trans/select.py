from copy import deepcopy
from logging import getLogger
from numpy import in1d, array, where

lg = getLogger('phypno')


def _select_trial(output, trial):

    trial_as_index = array(trial)
    if hasattr(output, 'time'):
        output.time = output.time[trial_as_index]
    if hasattr(output, 'freq'):
        output.freq = output.freq[trial_as_index]
    output.data = output.data[trial_as_index]

    return output


def _select_chan(output, chan):
    chan = array(chan, dtype='U')

    idx_chan = in1d(output.chan_name, chan)

    lg.info('Selecting {0: 3} channels out of {0: 3}'.format(
            len(where(idx_chan)[0]), len(output.chan_name)))
    for i in range(len(output.data)):
        output.data[i] = output.data[i][idx_chan, ...]
    output.chan_name = output.chan_name[idx_chan]

    return output


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


def _select_freq(output, freq):
    """Select time window for each trial.

    Parameters
    ----------
    output : instance of phypno.DataTime

    freq : tuple of 2 float
        which frequency interval you want.

    Returns
    -------
    instance of phypno.DataFreq
        where only the frequency band of interest is selected.

    Notes
    -----
    Some trials might be empty.

    """
    for i in range(len(output.data)):
        begfrq = int(where(output.freq[i] >= freq[0])[0][0])
        endfrq = int(where(output.freq[i] >= freq[1])[0][0])
        lg.info('Trial {0: 3}: selecting {0: 3}-{1: 3} Hz, while data ' +
                'is between {2: 3}-{3: 3} Hz'.format(i,
                                                     freq[0], freq[1],
                                                     output.freq[0][0],
                                                     output.freq[0][-1]))
        lg.debug('Selecting first sample {0: 5} and last sample '
                 '{1: 5}'.format(begfrq, endfrq))

        output.freq[i] = output.freq[i][begfrq:endfrq]
        output.data[i] = output.data[i][:, :, begfrq:endfrq]
    return output


class Select:
    """Define the selection of channel, time points, frequency.

    Parameters
    ----------
    trial : list of int or ndarray (dtype='i')
        index of trials of interest
    chan : list of str
        which channels you want
    time : tuple of 2 float
        which periods you want. If one of the tuple is None, keep it.
    freq : tuple of 2 float
        which frequency you want. If one of the tuple is None, keep it.

    Returns
    -------
    instance as the input.

    Notes
    -----
    Calling this class returns a class of the same type as the input class.
    If you want to subselect some data parts, you can call the classes in
    datatype directly.

    """
    def __init__(self, trial=None, chan=None, time=None, freq=None):
        """Design the selection of channels.


        """
        self.trial = trial
        self.chan = chan
        self.time = time
        self.freq = freq

    def __call__(self, data):
        output = deepcopy(data)

        if self.trial is not None:
            output = _select_trial(output, self.trial)
        if self.chan is not None:
            output = _select_chan(output, self.chan)
        if self.time is not None:
            output = _select_time(output, self.time)
        if self.freq is not None:
            output = _select_freq(output, self.freq)
        return output
