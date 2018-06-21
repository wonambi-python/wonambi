from json import dump
from numpy import array

from .brainvision import write_brainvision
from ..utils import MissingDependency

try:
    from bidso import iEEG
    from bidso.utils import replace_extension, replace_underscore
except ImportError as err:
    iEEG = replace_extension = MissingDependency(err)


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

        sampling_freq = set(self.task.channels.get(map_lambda=lambda x: x['sampling_frequency']))
        if len(sampling_freq) > 1:
            raise ValueError('Multiple sampling frequencies not supported')

        s_freq = float(next(iter(sampling_freq)))
        chan_name = self.task.channels.get(map_lambda=lambda x: x['name'])
        self.chan_name = array(chan_name)

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
        return self.baseformat.dataset.return_dat(chan, begsam, endsam)

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
        for mrk in self.task.events.tsv:
            markers.append({
                'start': float(mrk['onset']),
                'end': float(mrk['onset']) + float(mrk['duration']),
                'name': mrk['trial_type']
            })

        return markers


def write_bids(data, filename, markers=[]):
    write_brainvision(data, filename, markers)
    _write_ieeg_json(
        replace_extension(filename, '.json'))
    _write_ieeg_channels(
        replace_underscore(filename, 'channels.tsv'), data)
    _write_ieeg_events(
        replace_underscore(filename, 'events.tsv'), markers)


def _write_ieeg_json(output_file):
    """Use only required fields
    """
    dataset_info = {
        "TaskName": "unknown",
        "Manufacturer": "n/a",
        "PowerLineFrequency": 50,
        "iEEGReference": "n/a",
        }

    with output_file.open('w') as f:
        dump(dataset_info, f, indent=' ')


def _write_ieeg_channels(output_file, data):
    """
    TODO
    ----
    Make sure that the channels in all the trials are the same.
    """
    CHAN_TYPE = 'ECOG'
    CHAN_UNIT = 'µV'

    with output_file.open('w') as f:
        f.write('name\ttype\tunits\tsampling_frequency\tlow_cutoff\thigh_cutoff\tnotch\treference\n')
        for one_chan in data.chan[0]:
            f.write('\t'.join([
                one_chan,
                CHAN_TYPE,
                CHAN_UNIT,
                f'{data.s_freq:f}',
                'n/a',
                'n/a',
                'n/a',
                'n/a',
                ]) + '\n')


def _write_ieeg_events(output_file, markers):

    with output_file.open('w') as f:
        f.write('onset\tduration\ttrial_type\n')
        for mrk in markers:
            onset = mrk['start']
            duration = mrk['end'] - mrk['start']
            f.write(f'{onset:f}\t{duration:f}\t{mrk["name"]}\n')
