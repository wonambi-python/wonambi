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
    filename = None
    values = {}

    def __init__(self, filename):
        self.filename = Path(filename).resolve()
        for entity in BIDS_ENTITIES:
            self.values[entity] = _match(self.filename, f'{entity}-([a-zA-Z0-9-]+)_')

        if self.filename.name.endswith('.nii.gz'):
            self.extension = '.nii.gz'
        else:
            self.extension = self.filename.suffix

        self.format = _match(self.filename, f'_([a-zA-Z0-9-]+){self.extension}')

    def get_filename(self):
        pass
