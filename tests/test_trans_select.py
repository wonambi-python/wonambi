from numpy import arange
from numpy.random import seed
from numpy.testing import assert_array_equal, assert_array_almost_equal
from pytest import approx, raises

from wonambi import Dataset
from wonambi.attr import Annotations
from wonambi.utils import create_data
from wonambi.trans import select, resample, frequency, get_times, fetch
from wonambi.trans.select import _create_subepochs

from .paths import (annot_psg_path,
                    gui_file,
                    )

seed(0)
data = create_data(n_trial=5)


def test_select_typeerror():
    with raises(TypeError):
        select(data, trial=1)

    with raises(TypeError):
        select(chan='chan01')

    with raises(TypeError):
        select(data, time=1, chan=('chan01', ))


def test_select_trial():

    data1 = select(data, trial=(1, 2))
    assert data1.number_of('trial') == 2

    data1 = select(data, trial=(0, 0))
    assert_array_equal(data1.data[0], data1.data[1])
    assert len(data1.axis['chan']) == 2
    assert data1.number_of('trial') == 2


def test_select_string_selection():
    data1 = select(data, chan=['chan02'])
    assert data1.axis['chan'][0][0] == 'chan02'
    assert data1.data[0].shape[0] == 1


def test_select_empty_selection():
    data1 = select(data, chan=[])
    assert len(data1.axis['chan'][0]) == 0
    assert data1.data[0].shape[0] == 0


def test_select_create_subepochs():

    # 1d
    x = arange(1000)
    nperseg = 100
    step = 50
    v = _create_subepochs(x, nperseg, step)
    assert v.shape == (19, nperseg)
    assert v[0, step] == v[1, 0]

    # 2d
    x = arange(1000).reshape(20, 50)
    nperseg = 10
    step = 5
    v = _create_subepochs(x, nperseg, step)
    assert v.shape == (20, 9, nperseg)
    assert_array_equal(v[:, 0, step], v[:, 1, 0])

    # 3d
    x = arange(1000).reshape(4, 5, 50)
    v = _create_subepochs(x, nperseg, step)
    assert v.shape == (4, 5, 9, nperseg)
    assert_array_equal(v[..., 0, step], v[..., 1, 0])


def test_select_trials():
    data1 = select(data, trial=(1, 4))
    assert_array_equal(data.data[1], data1.data[0])


def test_select_trials_and_string():
    data1 = select(data, trial=(1, 4), chan=('chan01', 'chan02'))
    assert len(data1.axis['chan']) == 2
    assert len(data1.axis['chan'][0]) == 2


def test_select_trials_and_string_invert():
    data1 = select(data, trial=(1, 4), chan=('chan01', 'chan02'), invert=True)
    assert len(data1.axis['chan']) == data.number_of('trial') - 2
    assert len(data1.axis['chan'][0]) == data.number_of('chan')[0] - 2


def test_select_interval():
    data1 = select(data, time=(0.2, 0.5))

    assert data1.axis['time'][0].shape[0] == 76
    assert data1.data[0].shape[1] == 76
    assert data1.data[-1].shape[1] == 76


def test_select_interval_invert():
    data1 = select(data, time=(0.2, 0.5), invert=True)
    assert data1.number_of('time')[0] == data.number_of('time')[0] - 76
    assert data1.data[0].shape[1] == data.number_of('time')[0] - 76
    assert data1.data[-1].shape[1] == data.number_of('time')[0] - 76

    data2 = select(data1, time=(0.2, 0.5), invert=True)
    assert data1.number_of('trial') == data2.number_of('trial')


def test_select_interval_not_in_data():
    data1 = select(data, time=(10.2, 10.5))

    assert len(data1.axis['time'][0]) == 0
    assert data1.data[0].shape[1] == 0
    assert data1.data[-1].shape[1] == 0


def test_select_oneside_interval_0():
    data1 = select(data, time=(None, 0.5))

    assert len(data1.axis['time'][0]) * 2 == len(data.axis['time'][0])
    assert data1.data[0].shape[1] * 2 == data.data[0].shape[1]
    assert data1.axis['time'][0][0] == 0
    assert data1.axis['time'][0][-1] < .5


def test_select_oneside_interval_1():
    data1 = select(data, time=(0.5, None))

    assert len(data1.axis['time'][0]) * 2 == len(data.axis['time'][0])
    assert data1.data[0].shape[1] * 2 == data.data[0].shape[1]
    assert data1.axis['time'][0][0] >= 0.5
    assert data1.axis['time'][0][-1] == data.axis['time'][0][-1]


def test_select_oneside_interval_both():
    data1 = select(data, time=(None, None))

    assert len(data1.axis['time'][0]) == len(data.axis['time'][0])
    assert data1.data[0].shape[1] == data.data[0].shape[1]
    assert data1.axis['time'][0][0] == data.axis['time'][0][0]
    assert data1.axis['time'][0][-1] == data.axis['time'][0][-1]


def test_resample():
    seed(0)
    data = create_data(n_trial=1, s_freq=1024, signal='sine', sine_freq=20)

    NEW_FREQ = 256
    data1 = resample(data, s_freq=NEW_FREQ)

    assert data1.s_freq == NEW_FREQ
    assert data1.data[0].shape[1] == data1.number_of('time')[0]

    freq = frequency(data, taper='boxcar')
    freq1 = frequency(data1, taper='boxcar')
    assert_array_almost_equal(sum(freq.data[0][0, :]),
                              sum(freq1.data[0][0, :]),
                              4)
    
def test_get_times():
    annot = Annotations(str(annot_psg_path))
    
    bundles = get_times(annot, stage=['NREM2'], exclude=True)
    assert len(bundles[0]['times']) == 229
    assert bundles[0]['stage'] == 'NREM2'
    
def test_fetch():
    dset = Dataset(str(gui_file))
    annot = Annotations(str(annot_psg_path))
    
    seg = fetch(dset, annot, stage=['NREM2', 'NREM3'], epoch='locked',
                         reject_epoch=True, reject_artf=True)
    assert len(seg) == 356
    
    seg = fetch(dset, annot, cat=(0, 1, 0, 0), 
                         stage=['NREM2', 'NREM3'], reject_epoch=True, 
                         reject_artf=True)
    assert len(seg) == 31
    assert seg[14]['times'][0] == (34380, 34410)
    
    seg = fetch(dset, annot, cat=(0, 0, 1, 0), stage=['NREM1'])
    seg.read_data(['EEG Fpz-Cz'], ref_chan=['EEG Pz-Oz'])
    assert seg[0]['data']()[0][0].shape == (297000,)
    assert approx(seg[0]['data']()[0][0][100]) == -4.3201466  
