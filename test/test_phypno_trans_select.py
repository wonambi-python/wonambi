from . import *

from os.path import join

from phypno import Dataset
from phypno.trans import Select
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


def test_select_interval():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    TIME = (0.2, 0.5)
    s = Select(time=TIME)
    data1 = s(data)
    assert data1.axis['time'][0].shape[0] == 153
    assert data1.data[0].shape[1] == 153
    assert data1.data[8].shape[1] == 153
