from copy import deepcopy
from logging import getLogger
from numpy import where

lg = getLogger('phypno')


def _select_chan(output, chan):
    idx = []
    for ch in chan:
        idx.append(output.chan_name.index(ch))

    lg.info('Selecting {0: 3} channels out of {0: 3}'.format(
            len(idx), len(output.chan_name)))
    output.data = output.data[idx, :]
    output.chan_name = chan
    return output


def _select_time(output, time):
    begsam = int(where(output.time >= time[0])[0][0])
    endsam = int(where(output.time >= time[1])[0][0])
    lg.info('Selecting {0: 3}-{1: 3} time, while data is between '
            '{2: 3}-{3: 3}'.format(time[0], time[1],
                                   output.time[0], output.time[-1]))
    lg.debug('Selecting first sample {0: 5} and last sample '
             '{1: 5}'.format(begsam, endsam))

    output.time = output.time[begsam:endsam]
    output.data = output.data[:, begsam:endsam, ...]
    return output


def _select_freq(output, freq):
    begfrq = int(where(output.freq >= freq[0])[0][0])
    endfrq = int(where(output.freq >= freq[1])[0][0])
    lg.info('Selecting {0: 3}-{1: 3} Hz, while data is between '
            '{2: 3}-{3: 3} Hz'.format(freq[0], freq[1],
                                   output.freq[0], output.freq[-1]))
    lg.debug('Selecting first sample {0: 5} and last sample '
             '{1: 5}'.format(begfrq, endfrq))

    output.freq = output.freq[begfrq:endfrq]
    output.data = output.data[:, :, begfrq:endfrq]
    return output


class Select:
    """Define the selection of channel, time points, frequency.

    Parameters
    ----------
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
    def __init__(self, chan=None, time=None, freq=None):
        """Design the selection of channels.


        """
        self.chan = chan
        self.time = time
        self.freq = freq

    def __call__(self, data):
        output = deepcopy(data)

        if self.chan:
            output = _select_chan(output, self.chan)
        if self.time:
            output = _select_time(output, self.time)
        if self.freq:
            output = _select_freq(output, self.freq)
        return output
