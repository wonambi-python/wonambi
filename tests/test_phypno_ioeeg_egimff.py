from numpy import isnan
from numpy.testing import assert_array_almost_equal

from phypno import Dataset

from .utils import IO_PATH

mff_file = IO_PATH / 'egi.mff'

d = Dataset(mff_file)

def test_mff_read():
    d.read_data(begtime=10, endtime=20)


def test_mff_before_start():

    data = d.read_data(begsam=-100, endsam=10)
    assert isnan(data.data[0][0, 0])


def test_mff_after_end():
    n_samples = d.header['n_samples']
    data = d.read_data(begsam=n_samples - 100, endsam=n_samples + 100)
    assert isnan(data.data[0][0, -1])
