from zipfile import ZipFile
from urllib.request import urlopen
from shutil import copyfileobj
from os import environ
from pathlib import Path

test_path = Path(__file__).resolve().parent
test_txt = test_path / 'Public' / 'test.txt'


def test_download_datasets():
    url = environ['DATA_URL']
    print(len(url))
    file_name = test_path / 'download.zip'

    with urlopen(url) as response, file_name.open('wb') as out_file:
        copyfileobj(response, out_file)

    with ZipFile(file_name) as zf:
        zf.extractall(test_path)

    assert test_txt.exists()


def test_read_text():
    with test_txt.open() as f:
        assert f.read() == 'aaaa'

