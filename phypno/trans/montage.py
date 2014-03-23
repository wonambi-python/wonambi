from logging import getLogger
lg = getLogger('phypno')

from copy import deepcopy

from numpy import mean

from . import Math, Select


class Montage:
    """Apply linear transformation to the channels.

    Parameters
    ----------

    Attributes
    ----------

    Notes
    -----

    """
    def __init__(self, ref_chan=None, ref_to_avg=False):
        if ref_to_avg and ref_chan is not None:
            raise TypeError('You cannot specify reference to the average and '
                            'the channels to use as reference')

        if ref_chan is not None:
            if not isinstance(ref_chan, (list, tuple)):
                if not all(isinstance(x, str) for x in ref_chan):
                    raise TypeError('chan should be a list of strings')

        self.ref_chan = ref_chan
        self.ref_to_avg = ref_to_avg

    def __call__(self, data):
        """Apply the montage to the data.

        Parameters
        ----------
        data : instance of DataRaw
            the data to filter

        Returns
        -------
        filtered_data : instance of DataRaw
            filtered data

        """
        mdata = deepcopy(data)

        if self.ref_to_avg or len(self.ref_chan) > 0:

            for i in range(mdata.number_of('trial')):
                if self.ref_to_avg:
                    self.ref_chan = data.axis['chan'][0]

                ref_data = mdata(trial=i, chan=self.ref_chan)
                mdata.data[i] = (mdata(trial=i) -
                                 mean(ref_data,
                                      axis=mdata.index_of('chan')))

        return mdata
