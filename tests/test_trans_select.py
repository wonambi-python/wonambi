from numpy import arange
from numpy.random import seed
from numpy.testing import assert_array_equal, assert_array_almost_equal
from pytest import raises

from wonambi.utils import create_data
from wonambi.trans import select, resample, frequency
from wonambi.trans.select import _create_subepochs


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
