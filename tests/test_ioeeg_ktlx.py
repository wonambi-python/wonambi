from numpy.testing import assert_array_almost_equal

from wonambi import Dataset

from .paths import ktlx_file


def test_xltek_data():
    d = Dataset(ktlx_file)
    data = d.read_data(begsam=223380, endsam=223381, chan=('Fz', ))
    assert_array_almost_equal(data.data[0][0, 0], -2021.171532)


def test_xltek_marker():
    d = Dataset(ktlx_file)
    markers = d.read_markers()
    assert markers[0]['name'] == 'Gain/Filter change (-unknown-)'
    assert markers[-1]['end'] == 1052.1
