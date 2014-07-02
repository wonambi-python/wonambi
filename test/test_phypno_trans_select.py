from . import *

from os.path import join

from numpy import sum, sin, pi
from scipy.signal import welch

from phypno import Dataset
from phypno.trans import Select, Resample
from phypno.utils import create_data

edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(['LOF4', 'LOF5'], begtime=0, endtime=5)


@raises(TypeError)
def test_select_one_value_trial():
    lg.info('---\nfunction: ' + stack()[0][3])

    Select(trial=0)


@raises(TypeError)
def test_select_one_value_str():
    lg.info('---\nfunction: ' + stack()[0][3])

    Select(chan='chan01')


@raises(TypeError)
def test_select_one_value_float():
    lg.info('---\nfunction: ' + stack()[0][3])

    Select(time=1, chan=('chan01', ))


def test_select_trial():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(trial=(0, 0))
    data1 = s(data)
    assert_array_equal(data1.data[0], data1.data[1])
    assert len(data1.axis['chan']) == 2
    assert data1.number_of('trial') == 2


def test_select_string_selection():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(chan=['LOF4'])
    data1 = s(data)
    assert data1.axis['chan'][0][0] == 'LOF4'
    assert data1.data[0].shape[0] == 1


def test_select_empty_selection():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(chan=[])
    data1 = s(data)
    assert len(data1.axis['chan'][0]) == 0
    assert data1.data[0].shape[0] == 0


data = create_data(n_trial=10)


def test_select_trials():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(trial=(1, 5))
    data1 = s(data)
    assert_array_equal(data.data[1], data1.data[0])


def test_select_trials_and_string():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    s = Select(trial=(1, 5), chan=('chan01', 'chan02'))
    data1 = s(data)
    assert len(data1.axis['chan']) == 2
    assert len(data1.axis['chan'][0]) == 2


def test_select_trials_and_string_invert():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    s = Select(trial=(1, 5), chan=('chan01', 'chan02'), invert=True)
    data1 = s(data)
    assert len(data1.axis['chan']) == data.number_of('trial') - 2
    assert len(data1.axis['chan'][0]) == data.number_of('chan') - 2


def test_select_interval():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    TIME = (0.2, 0.5)
    s = Select(time=TIME)
    data1 = s(data)
    assert data1.axis['time'][0].shape[0] == 153
    assert data1.data[0].shape[1] == 153
    assert data1.data[8].shape[1] == 153


def test_select_interval_invert():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    TIME = (0.2, 0.5)
    s = Select(time=TIME, invert=True)
    data1 = s(data)
    assert data1.number_of('time')[0] == data.number_of('time')[0] - 153
    assert data1.data[0].shape[1] == data.number_of('time')[0] - 153
    assert data1.data[8].shape[1] == data.number_of('time')[0] - 153


def test_select_interval_not_in_data():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    TIME = (10.2, 10.5)
    s = Select(time=TIME)
    data1 = s(data)
    assert len(data1.axis['time'][0]) == 0
    assert data1.data[0].shape[1] == 0
    assert data1.data[8].shape[1] == 0


def test_select_oneside_interval_0():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    TIME = (None, 0.5)
    s = Select(time=TIME)
    data1 = s(data)
    assert len(data1.axis['time'][0]) * 2 == len(data.axis['time'][0])
    assert data1.data[0].shape[1] * 2 == data.data[0].shape[1]
    assert data1.axis['time'][0][0] == 0
    assert data1.axis['time'][0][-1] < .5


def test_select_oneside_interval_1():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    TIME = (0.5, None)
    s = Select(time=TIME)
    data1 = s(data)
    assert len(data1.axis['time'][0]) * 2 == len(data.axis['time'][0])
    assert data1.data[0].shape[1] * 2 == data.data[0].shape[1]
    assert data1.axis['time'][0][0] >= 0.5
    assert data1.axis['time'][0][-1] == data.axis['time'][0][-1]


def test_select_oneside_interval_both():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    TIME = (None, None)
    s = Select(time=TIME)
    data1 = s(data)
    assert len(data1.axis['time'][0]) == len(data.axis['time'][0])
    assert data1.data[0].shape[1] == data.data[0].shape[1]
    assert data1.axis['time'][0][0] == data.axis['time'][0][0]
    assert data1.axis['time'][0][-1] == data.axis['time'][0][-1]


def test_resample():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=1, n_chan=1)

    data.data[0][0, :] = sin(20 * 2 * pi * data.axis['time'][0])

    NEW_FREQ = 100
    res = Resample(s_freq=NEW_FREQ)
    data1 = res(data)
    assert float(data1.s_freq) == float(NEW_FREQ)
    assert data.data[0].shape[1] == data.number_of('time')[0]

    f, Pxx = welch(data(trial=0, chan=data.axis['chan'][0]),
                   fs=data.s_freq, nperseg=data.s_freq)
    f1, Pxx1 = welch(data1(trial=0, chan=data.axis['chan'][0]),
                     fs=data1.s_freq, nperseg=data1.s_freq)

    assert_array_almost_equal(sum(Pxx), sum(Pxx1))
