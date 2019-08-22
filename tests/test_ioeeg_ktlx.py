from numpy.testing import assert_array_almost_equal
from pytest import raises

from wonambi import Dataset

from .paths import ktlx_file


def test_xltek_data():
    d = Dataset(ktlx_file)
    data = d.read_data(begsam=1000, endsam=1001, chan=('FZ', ))
    assert_array_almost_equal(data.data[0][0, 0], -90.119315)


def test_xltek_marker():
    d = Dataset(ktlx_file)
    markers = d.read_markers()
    assert markers[0]['name'] == 'Start Recording (varkha)'
    assert int(markers[-1]['end']) == 1314


def test_xltek_videos():
    d = Dataset(ktlx_file)

    with raises(IndexError):
        d.read_videos(0, 2)

    videos, v_beg, v_end = d.read_videos(100, 200)
    assert len(videos) == 2
    assert v_beg == 58.410209
    assert v_end == 37.177808
