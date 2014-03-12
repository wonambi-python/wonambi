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
from os.path import join
from numpy import arange
from phypno import Dataset
from phypno.trans import Freq, TimeFreq


edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LOF1', 'LOF2', 'LMF6'], begtime=0, endtime=60)


def test_DataTime_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    time_limits = (0, 1)
    sel_dat, sel_time = data(time=time_limits)
    assert sel_time[0] == data.time[0]
    assert sel_time[-1] <= time_limits[1]
    assert sel_time.shape[0] == sel_dat.shape[1]
    assert sel_dat.shape[0] == 3


def test_DataTime_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    chan_limits = ['LOF1', 'LOF2']
    sel_dat, sel_time = data(chan=chan_limits)
    assert sel_time.shape[0] == sel_dat.shape[1]
    assert sel_dat.shape[0] == 2


def test_DataTime_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    subdata = d.read_data(chan=['LOF1', 'LOF2'], begtime=0, endtime=1)
    dat1, time1 = subdata()
    dat2, time2 = data(chan=['LOF1', 'LOF2'], time=(0, 1))
    assert_array_equal(dat1, dat2)
    assert_array_equal(time1, time2)


calc_freq = Freq()
freq = calc_freq(data)


def test_DataFreq_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    assert len(freq.data.shape) == 3
    assert freq.data.shape[1] == 1  # time is always one
    assert freq.data.shape[2] > 1


def test_DataFreq_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    dat1, freq1 = freq()
    assert len(dat1.shape) == 2
    assert len(freq1) == freq.data.shape[2]


def test_DataFreq_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    freq_limits = (10, 25)
    dat1, freq1 = freq(freq=freq_limits)
    assert freq1[0] >= freq_limits[0]
    assert freq1[-1] <= freq_limits[1]


TOI = arange(2, 8)
calc_tf = TimeFreq(toi=TOI)
tf = calc_tf(data)


def test_DataTimeFreq_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    assert len(tf.data.shape) == 3
    assert tf.data.shape[1] == len(TOI)
    assert tf.data.shape[2] > 1


def test_DataTimeFreq_02():
    chan_limits = ['LOF1', 'LOF2']
    time_limits = (4, 5)
    sel_dat, sel_time, sel_freq = tf(chan=chan_limits, time=time_limits)
    assert sel_dat.shape[0] == 2
    assert sel_time.shape[0] == 1


def test_DataTimeFreq_03():
    time_limits = (4, 5)
    freq_limits = (10, 25)
    sel_dat, sel_time, sel_freq = tf(freq=freq_limits, time=time_limits)
    assert sel_dat.shape[0] == 3
    assert sel_time.shape[0] == 1
    assert sel_dat.shape[2] == 15
