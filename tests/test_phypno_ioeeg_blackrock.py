from numpy.testing import assert_array_almost_equal

from phypno import Dataset

from .utils import IO_PATH, DOWNLOADS_PATH

nev_file = IO_PATH / 'blackrock' / 'blackrock.nev'
ns2_file = IO_PATH / 'blackrock' / 'blackrock.ns2'
ns4_file = DOWNLOADS_PATH / 'sampleData' / 'sampleData.ns4'


def test_blackrock_ns_01():
    d = Dataset(ns4_file)
    data = d.read_data(begsam=100, endsam=101, chan=('ainp2', ))
    assert_array_almost_equal(data.data[0][0, 0], -2625.35477767)

    d.read_data(begsam=-100, endsam=-10)
    d.read_data(begsam=1206061, endsam=1206070)


def test_blackrock_ns_02():
    Dataset(str(ns4_file))


def test_blackrock_ns_03():
    Dataset(ns2_file)


def test_blackrock_nev_01():
    d = Dataset(nev_file)
    markers = d.read_markers()
    assert markers[0]['name'] == '255'
    assert markers[-1]['end'] == 1442.3611
