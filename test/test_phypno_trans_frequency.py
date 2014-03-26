from . import *

from phypno import Dataset
from phypno.utils import create_data
from phypno.trans import Freq, TimeFreq


edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LMF6'], begtime=0, endtime=10)
data.s_freq = 512


def test_freq_basic():
    lg.info('---\nfunction: ' + stack()[0][3])

    calc_freq = Freq()
    freq = calc_freq(data)
    assert freq.list_of_axes == ('chan', 'freq')
    assert_almost_equal(freq(trial=0, chan='LMF6', freq=10),
                        36.0515022277)


def test_freq_option():
    lg.info('---\nfunction: ' + stack()[0][3])

    calc_freq = Freq(scaling='spectrum')
    freq = calc_freq(data)
    assert_almost_equal(freq(trial=0, chan='LMF6', freq=10),
                        108.15450286865234)


@raises(ValueError)
def test_freq_methoderror():
    lg.info('---\nfunction: ' + stack()[0][3])

    Freq(method='nonexistent')


@raises(TypeError)
def test_freq_typeerror():
    lg.info('---\nfunction: ' + stack()[0][3])

    wrong_data = create_data(datatype='ChanFreq')
    calc_freq = Freq()
    calc_freq(wrong_data)

