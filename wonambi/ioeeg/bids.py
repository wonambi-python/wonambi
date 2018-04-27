from datetime import datetime
from pathlib import Path
try:
    from bidso import iEEG
except ImportError:
    iEEG = None


class BIDS:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory
    """
    def __init__(self, filename):
        from ..dataset import Dataset
        self.filename = filename
        self.task = iEEG(filename)

        self.baseformat = Dataset(filename)

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
        subj_id = self.task.subject

        sampling_freq = set(self.task.channels.get(map_lambda=lambda x:x['sampling_frequency']))
        if len(sampling_freq) > 1:
            raise ValueError('Multiple sampling frequencies not supported')

        s_freq = float(next(iter(sampling_freq)))
        chan_name = self.task.channels.get(map_lambda=lambda x: x['name'])


        # read these values directly from dataset
        orig = self.baseformat.header
        start_time = orig['start_time']
        n_samples = orig['n_samples']

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
        return self.baseformat.read_data(chan, begsam, endsam)

    def return_markers(self):
        """Return all the markers (also called triggers or events).

        Returns
        -------
        list of dict
            where each dict contains 'name' as str, 'start' and 'end' as float
            in seconds from the start of the recordings, and 'chan' as list of
            str with the channels involved (if not of relevance, it's None).
        """
        markers = []
        for v in self.mrk['Marker Infos'].values():
            if v[0] == 'New Segment':
                continue

            markers.append({
                'name': v[1],
                'start': float(v[2]) / self.s_freq,
                'end': (float(v[2]) + float(v[3])) / self.s_freq,
                })

        return markers
