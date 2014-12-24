from pickle import load

from numpy import hstack


class Phypno:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    """
    def __init__(self, filename):
        self.filename = filename
        with open(filename, 'rb') as f:
            self._data = load(f)

        # transform data using NaN, based on time information

    def return_hdr(self):
        """Return the header for further use.

        Returns
        -------
        subj_id : str
            subject identification code
        start_time : datetime
            start time of the dataset
        s_freq : float
            sampling frequency
        chan_name : list of str
            list of all the channels
        n_samples : int
            number of samples in the dataset
        orig : dict
            additional information taken directly from the header

        """
        subj_id = str()
        start_time = self._data.start_time
        s_freq = self._data.s_freq
        chan_name = self._data.axis['chan'][0]
        n_samples = sum(self._data.number_of('time'))
        orig = dict()

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

    def return_dat(self, chan, begsam, endsam):
        """Return the data as 2D numpy.ndarray.

        Parameters
        ----------
        chan : int or list
            index (indices) of the channels to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A 2d matrix, with dimension chan X samples

        """
        data = hstack(self._data.data)  # simple concatenation
        return data[chan, begsam:endsam]

    def return_markers(self):
        """Return all the markers (also called triggers or events).

        Returns
        -------
        list of dict
            where each dict contains 'name' as str, 'start' and 'end' as float
            in seconds from the start of the recordings, and 'chan' as list of
            str with the channels involved (if not of relevance, it's None).

        Raises
        ------
        FileNotFoundError
            when it cannot read the events for some reason (don't use other
            exceptions).
        """
        markers = [{'name': 'one_trigger',
                    'start': 10,
                    'end': 15,  # duration of 5s
                    'chan': ['chan1', 'chan2'],  # or None
                    }]
        return markers
