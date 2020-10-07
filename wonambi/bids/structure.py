from pathlib import Path
from numpy import ndarray

from .utils import _match, get_tsv, get_json
from ..dataset import Dataset


BIDS_ENTITIES = (
    'sub',
    'ses',
    'task',
    'acq',
    'ce',
    'rec',
    'dir',
    'run',
    'mod',
    'echo',
    'recording',
    'proc',
    'space',
    )


class BIDSName():
    values = {}

    def __init__(self, filename):
        self._filename = Path(filename).resolve()
        self.path = self._filename.parent
        for entity in BIDS_ENTITIES:
            self.values[entity] = _match(self._filename, f'{entity}-([a-zA-Z0-9-]+)_')

        if self._filename.name.endswith('.nii.gz'):
            self.extension = '.nii.gz'
        else:
            self.extension = self._filename.suffix

        self.format = _match(self._filename, f'_([a-zA-Z0-9-]+){self.extension}')

    @property
    def filename(self):
        return self.path / build_name(self.values, f'{self.format}{self.extension}')


def build_name(values, ending):
    parts = []
    for k, v in values.items():
        if v is None:
            continue
        parts.append(f'{k}-{v}')

    return '_'.join(parts) + '_' + ending


class BIDSMain(BIDSName):
    def __init__(self, filename):
        super().__init__(filename)

    @property
    def header(self):
        return get_json(self.path, self.values, f'{self.format}.json')

    @property
    def events(self):
        """
        TODO
        ----
        how to handle n/a
        """
        return get_tsv(self.path, self.values, 'events.tsv')


class BIDSEEG(BIDSMain):
    def __init__(self, filename):
        super().__init__(filename)

    def read_data(self, chan=None, begtime=None, endtime=None, events=None,
                  pre=1, post=1):
        """
        TODO
        ----
        rename channels using bids info
        """
        if chan is not None:
            if isinstance(chan, ndarray) and chan.dtype.names is not None:
                chan = chan['name']
            chan = list(chan)

        if events is not None:
            if isinstance(events, ndarray) and events.dtype.names is not None:
                events = events['onset']
            events = list(events)

        return Dataset(self.filename).read_data(
            chan=chan, begtime=begtime, endtime=endtime, events=events,
            pre=pre, post=post)

    @property
    def channels(self):
        return get_tsv(self.path, self.values, 'channels.tsv')

    @property
    def electrodes(self):
        return get_tsv(self.path, self.values, 'electrodes.tsv')
