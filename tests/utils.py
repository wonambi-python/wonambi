from pathlib import Path

test_path = Path(__file__).resolve().parent

DATA_PATH = test_path / 'data'

SAMPLE_PATH = DATA_PATH / 'Public'
ANNOT_PATH = SAMPLE_PATH / 'annot'
FREESURFER_HOME = SAMPLE_PATH / 'freesurfer'
SUBJECTS_DIR = SAMPLE_PATH / 'SUBJECTS_DIR'
IO_PATH = SAMPLE_PATH / 'io'

EXPORTED_PATH = test_path / 'exported'
EXPORTED_PATH.mkdir(exist_ok=True)

DOCS_PATH = test_path.parent / 'docs'
GUI_PATH = DOCS_PATH / 'source' / 'gui' / 'images'
GUI_PATH.mkdir(exist_ok=True)
VIZ_PATH = DOCS_PATH / 'source' / 'viz' / 'images'
VIZ_PATH.mkdir(exist_ok=True)
