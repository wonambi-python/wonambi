from copy import deepcopy
from logging import getLogger
from numpy import where

lg = getLogger('phypno')


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
    TODO: this should be part of datatype, so you can call it directly.
    It's more intuitive.

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
            idx = []
            for ch in self.chan:
                idx.append(data.chan_name.index(ch))

            lg.info('Selecting {0: 3} channels out of {0: 3}'.format(
                    len(idx), len(data.chan_name)))
            output.data = output.data[idx, :]
            output.chan_name = self.chan

        if self.time:
            begsam = int(where(data.time >= self.time[0])[0][0])
            endsam = int(where(data.time >= self.time[1])[0][0])
            lg.info('Selecting {0: 3}-{1: 3} time, while data is between '
                    '{2: 3}-{3: 3}'.format(self.time[0], self.time[1],
                                           data.time[0], data.time[-1]))
            lg.debug('Selecting first sample {0: 5} and last sample '
                     '{1: 5}'.format(begsam, endsam))

            output.time = data.time[begsam:endsam]
            if len(output.data.shape) == 2:
                output.data = output.data[:, begsam:endsam]
            else:
                raise NotImplementedError('You need to check when there are '
                                          'different n of dim')

        if self.freq:
            # remember to do output.data = output.data
            pass

        return output
