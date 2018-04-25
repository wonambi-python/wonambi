from numpy import isnan, dtype
from numpy.testing import assert_almost_equal
from pytest import raises

from wonambi import Dataset

from .paths import openephys_dir


def test_openephys_dataset_01():
    d = Dataset(openephys_dir)
    data = d.read_data(begtime=1, endtime=2)

    d = Dataset(openephys_dir)
    data = d.read_data(chan=['CH1', ], begsam=10, endsam=1400)
    assert data.data[0][0, 0]  == -132.6

    mrk = d.read_markers()
    assert len(mrk) == 0
