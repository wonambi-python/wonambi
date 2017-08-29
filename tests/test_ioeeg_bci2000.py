from wonambi import Dataset

from .utils import DATA_PATH

bci2000_file = DATA_PATH / 'bci2000.dat'


def test_bci2000_data():
    assert bci2000_file.exists()

    d = Dataset(bci2000_file)
    assert len(d.read_markers()) == 0

    data = d.read_data()
    assert data.data[0][0, 0] == 179.702
