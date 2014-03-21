from inspect import stack
from logging import getLogger
from numpy.testing import assert_array_equal
from nose.tools import raises
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

data_dir = '/home/gio/tools/phypno/data'

#-----------------------------------------------------------------------------#
from numpy import arange, array, empty
from numpy.random import random

from phypno import Data
from phypno.utils import create_data
data = create_data(n_trial=10, s_freq=500)


def test_data_select_trial():
    lg.info('---\nfunction: ' + stack()[0][3])

    output = data(trial=(1, 2, 3))
    assert len(output) == 3


def test_data_select_trial_compress():
    lg.info('---\nfunction: ' + stack()[0][3])

    output = data(trial=(1, ))
    assert len(output) == 1

    output = data(trial=1)
    assert output.shape == (8, 500)

    output = data(trial=(1, 2), squeeze=True)
    assert len(output) == 2


def test_data_select_one_dim():
    lg.info('---\nfunction: ' + stack()[0][3])

    TIME = data.dim['time'][0][:10]
    output = data(time=TIME)
    assert len(output) == 10
    assert output[0].shape[data.index_of('time')] == len(TIME)


def test_data_select_two_dim():
    lg.info('---\nfunction: ' + stack()[0][3])

    TIME = data.dim['time'][0][:10]
    CHAN = ('chan02', 'chan05')
    output = data(chan=CHAN, time=TIME)
    assert len(output) == 10
    assert output[0].shape == (len(CHAN), len(TIME))


def test_data_select_empty_selection():
    lg.info('---\nfunction: ' + stack()[0][3])

    TIME = (100, 200)
    CHAN = ('chan02', 'chan05')
    output = data(chan=CHAN, time=TIME)
    assert output[0].shape == (len(CHAN), 0)


def test_data_conserve_order():
    lg.info('---\nfunction: ' + stack()[0][3])

    CHAN = ('chan02', )
    output02 = data(chan=CHAN, trial=0)

    CHAN = ('chan05', )
    output05 = data(chan=CHAN, trial=0)

    CHAN = ('chan02', 'chan02')
    output02 = data(chan=CHAN, trial=0)

    CHAN = ('chan05', 'chan02')
    output0502 = data(chan=CHAN, trial=0)


def test_data_select_tolerance():
    lg.info('---\nfunction: ' + stack()[0][3])

    TIME = arange(0, 1, 0.05)
    output = data(time=TIME)
    assert output[0].shape[1] == 16  # without tolerance

    TIME = arange(0, 1, 0.05)
    CHAN = ('chan02', 'chan05')
    output = data(time=TIME, chan=CHAN, tolerance=1e-10)
    assert output[0].shape[1] == len(TIME)


def test_data_arbitrary_dimensions():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = Data()
    len_dim0 = 6
    data.dim['dim0'] = empty(1, dtype='O')
    data.dim['dim0'][0] = array(['x' + str(x) for x in range(len_dim0)],
                                dtype='U')
    len_dim1 = 10
    data.dim['dim1'] = empty(1, dtype='O')
    data.dim['dim1'][0] = arange(len_dim1)
    len_dim2 = 10
    data.dim['dim2'] = empty(1, dtype='O')
    data.dim['dim2'][0] = arange(len_dim2)
    len_dim3 = 5
    data.dim['dim3'] = empty(1, dtype='O')
    data.dim['dim3'][0] = arange(len_dim3)

    data.data = empty(1, dtype='O')
    data.data[0] = random((len_dim0, len_dim1, len_dim2, len_dim3))

    output = data(dim0=('x0', 'x3', 'x2'), dim1=(4, 6), dim2=(8, 1),
                  dim3=(0, 1, 2))
    assert output[0].shape == (3, 2, 2, 3)


# order!!!



from os.path import join
from phypno import Dataset
from phypno.trans import Freq, TimeFreq





edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LOF1', 'LOF2', 'LMF6'], begtime=0, endtime=60)


def test_DataTime_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    time_limits = (0, 1)
    sel_dat, sel_time = data(time=time_limits)
    assert sel_time[0][0] == data.time[0][0]
    assert sel_time[0][-1] <= time_limits[1]
    assert sel_time[0].shape[0] == sel_dat[0].shape[1]
    assert sel_dat[0].shape[0] == 3


def test_DataTime_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    chan_limits = ['LOF1', 'LOF2']
    sel_dat, sel_time = data(chan=chan_limits)
    assert sel_time[0].shape[0] == sel_dat[0].shape[1]
    assert sel_dat[0].shape[0] == 2


def test_DataTime_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    subdata = d.read_data(chan=['LOF1', 'LOF2'], begtime=0, endtime=1)
    dat1, time1 = subdata()
    dat2, time2 = data(chan=['LOF1', 'LOF2'], time=(0, 1))
    assert_array_equal(dat1[0], dat2[0])
    assert_array_equal(time1[0], time2[0])


calc_freq = Freq()
freq = calc_freq(data)


def test_DataFreq_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    assert len(freq.data[0].shape) == 3
    assert freq.data[0].shape[1] == 1  # time is always one
    assert freq.data[0].shape[2] > 1


def test_DataFreq_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    dat1, freq1 = freq()
    assert len(dat1[0].shape) == 2
    assert len(freq1[0]) == freq.data[0].shape[2]


def test_DataFreq_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    freq_limits = (10, 25)
    dat1, freq1 = freq(freq=freq_limits)
    assert freq1[0][0] >= freq_limits[0]
    assert freq1[0][-1] <= freq_limits[1]


TOI = arange(2, 8)
calc_tf = TimeFreq(toi=TOI)
tf = calc_tf(data)


def test_DataTimeFreq_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    assert len(tf.data[0].shape) == 3
    assert tf.data[0].shape[1] == len(TOI)
    assert tf.data[0].shape[2] > 1


def test_DataTimeFreq_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    chan_limits = ['LOF1', 'LOF2']
    time_limits = (4, 5)
    sel_dat, sel_time, sel_freq = tf(chan=chan_limits, time=time_limits)
    assert sel_dat[0].shape[0] == 2
    assert sel_time[0].shape[0] == 1


def test_DataTimeFreq_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    """This checks datatype DataTimeFreq
    time_limits = (4, 5)
    freq_limits = (10, 25)
    sel_dat, sel_time, sel_freq = tf(freq=freq_limits, time=time_limits)
    assert sel_dat[0].shape[0] == 3
    assert sel_time[0].shape[0] == 1
    assert sel_dat[0].shape[2] == 15
    """