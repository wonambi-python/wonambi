from . import *

from numpy import hstack, max, min, nan, nanargmax

from phypno.trans import Peaks
from phypno.utils import create_data

data = create_data(n_trial=10)


def test_peaks_default():
    lg.info('---\nfunction: ' + stack()[0][3])

    max_time = Peaks()
    max_data = max_time(data)

    assert len(max_data.list_of_axes) == 1
    chan = 'chan05'
    trl = 4
    idx_max = nanargmax(data(trial=trl, chan=chan))
    assert data.axis['time'][trl][idx_max] == max_data(trial=trl, chan=chan)


def test_peaks_default_chan():
    lg.info('---\nfunction: ' + stack()[0][3])

    max_chan = Peaks(axis='chan')
    max_data = max_chan(data)

    assert len(max_data.list_of_axes) == 1
    assert max_data.data[0].shape[0] == data.number_of('time')[0]


def test_peaks_default_limits():
    lg.info('---\nfunction: ' + stack()[0][3])

    LIMITS = (0, .2)
    max_time = Peaks(limits=LIMITS)
    max_data = max_time(data)
    x = hstack(max_data.data)

    assert max(x) < LIMITS[1]
    assert min(x) >= LIMITS[0]
