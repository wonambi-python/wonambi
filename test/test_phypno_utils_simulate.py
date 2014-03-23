from . import *

from phypno.utils import create_data


def test_simulate_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data()
    assert data.data.dtype == 'O'
    assert data.data.shape == (1,)  # one trial
    assert data.data[0].shape[0] == len(data.chan_name)
    assert data.data[0].shape[1] == len(data.time[0])


@raises(ValueError)
def test_simulate_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    create_data(datatype='xxx')


def test_simulate_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    N_TRIAL = 10
    data = create_data(n_trial=N_TRIAL)
    assert data.data.shape[0] == N_TRIAL


def test_simulate_04():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(datatype='DataFreq')
    assert data.data[0].shape[0] == len(data.chan_name)
    assert data.data[0].shape[1] == 1
    assert data.data[0].shape[2] == len(data.freq[0])


def test_simulate_05():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(datatype='DataTimeFreq')
    assert data.data[0].shape[0] == len(data.chan_name)
    assert data.data[0].shape[1] == len(data.time[0])
    assert data.data[0].shape[2] == len(data.freq[0])


def test_simulate_06():
    lg.info('---\nfunction: ' + stack()[0][3])

    TIME_LIMITS = (0, 10)
    data = create_data(time=TIME_LIMITS)
    assert data.time[0][0] == TIME_LIMITS[0]
    assert data.time[0][-1] < TIME_LIMITS[1]


def test_simulate_07():
    lg.info('---\nfunction: ' + stack()[0][3])

    FREQ_LIMITS = (0, 10)
    data = create_data(datatype='DataFreq', freq=FREQ_LIMITS)
    assert data.freq[0][0] == FREQ_LIMITS[0]
    assert data.freq[0][-1] < FREQ_LIMITS[1]
