from logging import getLogger

lg = getLogger('phypno')


class Select:
    """Class to select channel, time points, frequency.

    """
    def __init__(self, chan=None, time=None, freq=None):
        """Design the selection of channels.

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

        """
        self.chan = chan
        self.time = time
        self.freq = freq

    def __call__(self, data):
        if self.chan:
            idx = []
            for ch in self.chan:
                idx.append(data.chan_name.index(ch))

            lg.info('Selecting {0: 3} channels out of {0: 3}'.format(
                    len(idx), len(data.chan_name)))
            data.data = data.data[idx, :]
            data.chan_name = self.chan

        if self.time:
            pass

        if self.freq:
            pass

        return data
