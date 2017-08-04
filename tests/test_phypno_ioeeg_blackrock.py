from numpy.testing import assert_array_almost_equal

from phypno import Dataset

from .utils import IO_PATH

ns_file = IO_PATH / 'blackrock' / 'sampleData.ns4'
nev_file = IO_PATH / 'blackrock' / '03-142244-001.nev'


def test_blackrock_ns_01():
    d = Dataset(ns_file)
    data = d.read_data(begsam=100, endsam=101, chan=('ainp2', ))
    assert_array_almost_equal(data.data[0][0, 0], -2625.35477767)


def test_blackrock_ns_02():
    Dataset(str(ns_file))


def test_blackrock_nev_01():
    Dataset(nev_file)
