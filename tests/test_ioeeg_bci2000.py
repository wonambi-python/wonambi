from wonambi import Dataset

from .paths import bci2000_file


def test_bci2000_data():
    assert bci2000_file.exists()

    d = Dataset(bci2000_file)
    assert len(d.read_markers()) == 0

    data = d.read_data()
    assert data.data[0][0, 0] == 179.702
