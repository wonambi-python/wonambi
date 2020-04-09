from wonambi.bids.utils import _match
from pathlib import Path

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
        parts = []
        for k, v in self.values.items():
            if v is None:
                continue
            parts.append(f'{k}-{v}')

        stem = '_'.join(parts)
        return self.path / f'{stem}_{self.format}{self.extension}'
