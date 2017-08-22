from numpy import isnan
from numpy.testing import assert_array_almost_equal

from wonambi import Dataset

from .utils import DOWNLOADS_PATH

edf_file = DOWNLOADS_PATH / 'SC4031E0-PSG.edf'

d = Dataset(edf_file)


def test_edf_read():
    d.read_data(begtime=10, endtime=20)


def test_edf_before_start_both():
    data = d.read_data(begsam=-100, endsam=-10)
    assert isnan(data.data[0][0, 0])    
    

def test_edf_before_start():
    data = d.read_data(begsam=-100, endsam=10)
    assert isnan(data.data[0][0, 0])


def test_edf_after_end():
    n_samples = d.header['n_samples']
    data = d.read_data(begsam=n_samples - 100, endsam=n_samples + 100)
    assert isnan(data.data[0][0, -1])
