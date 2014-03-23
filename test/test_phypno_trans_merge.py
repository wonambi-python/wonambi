from . import *

from phypno.trans import Merge
from phypno.utils import create_data

data = create_data(n_trial=10)


def test_merge_along_time():
    lg.info('---\nfunction: ' + stack()[0][3])

    m_time = Merge('time')
    data1 = m_time(data)
    assert len(data1.axis['time']) == 1
    assert len(data1.axis['chan']) == 1
    assert len(data1.data) == 1
    assert data1.data[0].shape[1] == len(data1.axis['time'][0])


def test_merge_along_chan():
    lg.info('---\nfunction: ' + stack()[0][3])

    m_chan = Merge('chan')
    data1 = m_chan(data)
    assert len(data1.axis['time']) == 1
    assert len(data1.axis['chan']) == 1
    assert len(data1.data) == 1
    assert data1.data[0].shape[0] == len(data1.axis['chan'][0])


def test_merge_along_trial():
    lg.info('---\nfunction: ' + stack()[0][3])

    m_trial = Merge('trial')
    data1 = m_trial(data)
    assert len(data1.axis) == 3
    assert data1.index_of('trial_axis') == 2
    assert len(data1.data) == 1
    assert data1.data[0].shape[2] == data1.number_of('trial_axis')
