from pathlib import Path

from .utils import _match, get_tsv, get_json


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

    @property
    def channels(self):
        return get_tsv(self.path, self.values, 'channels.tsv')

    @property
    def electrodes(self):
        return get_tsv(self.path, self.values, 'electrodes.tsv')
