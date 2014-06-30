from . import *

from phypno.trans import Concatenate
from phypno.utils import create_data

data = create_data(n_trial=10)


def test_merge_along_time():
    lg.info('---\nfunction: ' + stack()[0][3])

    cat_time = Concatenate('time')
    data1 = cat_time(data)
    assert len(data1.axis['time']) == 1
    assert len(data1.axis['chan']) == 1
    assert len(data1.data) == 1
    assert data1.data[0].shape[1] == len(data1.axis['time'][0])


def test_merge_along_chan():
    lg.info('---\nfunction: ' + stack()[0][3])

    cat_chan = Concatenate('chan')
    data1 = cat_chan(data)
    assert len(data1.axis['time']) == 1
    assert len(data1.axis['chan']) == 1
    assert len(data1.data) == 1
    assert data1.data[0].shape[0] == len(data1.axis['chan'][0])


def test_merge_along_trial():
    lg.info('---\nfunction: ' + stack()[0][3])

    cat_trial = Concatenate('trial')
    data1 = cat_trial(data)
    assert len(data1.axis) == 3
    assert data1.index_of('trial_axis') == 2
    assert len(data1.data) == 1
    assert data1.data[0].shape[2] == data1.number_of('trial_axis')
