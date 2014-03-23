from . import *

from os.path import join
from phypno import Dataset
from phypno.trans import Freq, TimeFreq


edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LMF6'], begtime=0, endtime=10)


def test_freq_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    calc_freq = Freq()
    calc_freq(data)


@raises(TypeError)
def test_timefreq_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    tf = TimeFreq()  # without toi
    tf(data)


def test_timefreq_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    tf = TimeFreq(toi=range(2, 8))
    tf(data)
