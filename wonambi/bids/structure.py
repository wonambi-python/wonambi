from pathlib import Path
from json import load

from .utils import _match, read_tsv


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
    def _stem(self):
        parts = []
        for k, v in self.values.items():
            if v is None:
                continue
            parts.append(f'{k}-{v}')

        return '_'.join(parts)

    @property
    def filename(self):
        return self.path / f'{self._stem}_{self.format}{self.extension}'


class BIDSMain(BIDSName):
    def __init__(self, filename):
        super().__init__(filename)

    @property
    def _file_header(self):
        return self.path / f'{self._stem}_{self.format}.json'

    @property
    def header(self):
        with self._file_header.open() as f:
            return load(f)

    @property
    def _file_events(self):
        """
        TODO
        ----
        There might be a json file
        """
        return self.path / f'{self._stem}_events.tsv'

    @property
    def events(self):
        """
        TODO
        ----
        how to handle n/a
        """
        return read_tsv(self._file_events)


class BIDSEEG(BIDSMain):
    def __init__(self, filename):
        super().__init__(filename)

    @property
    def _file_channels(self):
        return self.path / f'{self._stem}_channels.tsv'

    @property
    def channels(self):
        return read_tsv(self._file_channels)

    @property
    def _file_electrodes(self):
        return self.path / f'{self._stem}_electrodes.tsv'

    @property
    def electrodes(self):
        return read_tsv(self._file_electrodes)
