from zipfile import ZipFile
from urllib.request import urlopen
from shutil import copyfileobj
from os import environ
from pathlib import Path

test_path = Path(__file__).resolve().parent
DATA_URL = environ['DATA_URL']

SAMPLE_PATH = test_path / 'Public'
FREESURFER_HOME = SAMPLE_PATH / 'freesurfer'
SUBJECTS_DIR = SAMPLE_PATH / 'SUBJECTS_DIR'
IO_PATH = SAMPLE_PATH / 'io'


def download_sample_data():
    file_name = test_path / 'sample_data.zip'

    with urlopen(DATA_URL) as response, file_name.open('wb') as out_file:
        copyfileobj(response, out_file)

    with ZipFile(file_name) as zf:
        zf.extractall(test_path)

download_sample_data()
