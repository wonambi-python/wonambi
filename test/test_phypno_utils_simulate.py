from inspect import stack
from logging import getLogger
from nose.tools import raises
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

#-----------------------------------------------------------------------------#
from phypno.utils import create_data

def test_simulate_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    data = create_data()
    assert data.data.shape[0] == len(data.chan_name)
    assert data.data.shape[1] == len(data.time)

@raises(ValueError)
def test_simulate_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    create_data(datatype='xxx')


def test_simulate_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    data = create_data(datatype='DataFreq')
    assert data.data.shape[0] == len(data.chan_name)
    assert data.data.shape[1] == 1
    assert data.data.shape[2] == len(data.freq)


def test_simulate_04():
    lg.info('---\nfunction: ' + stack()[0][3])
    data = create_data(datatype='DataTimeFreq')
    assert data.data.shape[0] == len(data.chan_name)
    assert data.data.shape[1] == len(data.time)
    assert data.data.shape[2] == len(data.freq)


def test_simulate_05():
    lg.info('---\nfunction: ' + stack()[0][3])
    TIME_LIMITS = (0, 10)
    data = create_data(time=TIME_LIMITS)
    assert data.time[0] == TIME_LIMITS[0]
    assert data.time[-1] < TIME_LIMITS[1]


def test_simulate_06():
    lg.info('---\nfunction: ' + stack()[0][3])
    FREQ_LIMITS = (0, 10)
    data = create_data(datatype='DataFreq', freq=FREQ_LIMITS)
    assert data.freq[0] == FREQ_LIMITS[0]
    assert data.freq[-1] < FREQ_LIMITS[1]
