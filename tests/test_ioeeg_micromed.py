from numpy import iinfo, isnan
from pytest import raises

from wonambi import Dataset

from .paths import micromed_file


def test_micromed_header():
    d = Dataset(micromed_file)
    assert d.header['chan_name'][-1] == 'EMG'
    assert d.header['chan_name'][:5] == ['FP1', 'FP2', 'AF7', 'AF3', 'AFz']
    assert d.header['subj_id'] == 'Tp_metrologie Tp_metrologie'

    orig = d.header['orig']
    assert orig['dvideo_begin'] == iinfo('u4').max

    markers = d.read_markers()
    assert len(markers) == 444
    assert markers[0]['name'] == '1'
    assert markers[0]['start'] == markers[0]['end']

    data = d.read_data(chan=('FP1', 'AFz'), begsam=10, endsam=20)
    assert data.data[0][1, 5] == -334.27734375

    data = d.read_data(chan=('FP1', 'AFz'), begsam=-10, endsam=20)
    assert all(isnan(data.data[0][1, :10]))

    data = d.read_data(chan=('FP1', 'AFz'), begsam=900, endsam=1010)
    assert all(isnan(data.data[0][1, -10:]))

    data = d.read_data(chan=('FP1', 'AFz'), begsam=-10, endsam=-2)
    assert all(isnan(data.data[0][1, :]))

    with raises(OSError):
        d.read_videos(10, 20)
