from nose.tools import raises
from os.path import abspath, join
from numpy.testing import assert_almost_equal

from numpy import arange, pi, sin

from phypno import Dataset
from phypno.utils import create_data
from phypno.trans import Freq, TimeFreq, Math

import phypno
data_dir = abspath(join(phypno.__path__[0], '..', 'data'))


edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LMF6'], begtime=0, endtime=10)
data.s_freq = 512


def test_freq_basic():
    calc_freq = Freq()
    freq = calc_freq(data)
    assert freq.list_of_axes == ('chan', 'freq')
    assert_almost_equal(freq(trial=0, chan='LMF6', freq=10),
                        49.15529248338329)


def test_freq_option():
    calc_freq = Freq(scaling='spectrum')
    freq = calc_freq(data)
    assert_almost_equal(freq(trial=0, chan='LMF6', freq=10),
                        36.86646936253747)


@raises(ValueError)
def test_freq_methoderror():
    Freq(method='nonexistent')


@raises(TypeError)
def test_freq_typeerror():
    wrong_data = create_data(datatype='ChanFreq')
    calc_freq = Freq()
    calc_freq(wrong_data)


@raises(ValueError)
def test_timefreq_methoderror():
    TimeFreq(method='nonexistent')


def test_timefreq_morlet():
    FOI = arange(5, 10)
    calc_tf = TimeFreq(foi=FOI)
    tf = calc_tf(data)

    assert tf.list_of_axes == ('chan', 'time', 'freq')
    assert tf.data[0].shape[0] == data.number_of('chan')[0]
    assert tf.data[0].shape[1] == data.number_of('time')[0]
    assert tf.data[0].shape[2] == len(FOI)
    x = tf(trial=0, chan='LMF6', time=tf.axis['time'][0][10])
    assert_almost_equal(x[0], (-220.22782600662993+221.15713670591379j))


def test_timefreq_example_in_doc():
    from phypno.trans import Math, TimeFreq
    calc_tf = TimeFreq(foi=(8, 10))
    tf = calc_tf(data)
    make_abs = Math(operator_name='abs')
    tf_abs = make_abs(tf)
    assert_almost_equal(tf_abs.data[0][0, 0, 0], 243.835870058669)


def test_timefreq_sine():
    FREQ = 10
    data = create_data(n_chan=1)
    data.data[0][0, :] = sin(2 * pi * data.axis['time'][0] * FREQ)

    FOI = arange(4, 20)
    calc_tf = TimeFreq(foi=FOI)
    tf = calc_tf(data)
    make_abs = Math(operator_name='abs')
    tf_abs = make_abs(tf)
    x = tf_abs(trial=0, chan='chan00')

    # peak in power spectrum is where the frequency of the sine wave
    assert FOI[x[200, :].argmax()] == FREQ


def test_timefreq_welch():
    calc_tf = TimeFreq(method='welch')
    tf = calc_tf(data)

    assert tf.list_of_axes == ('chan', 'time', 'freq')
    assert tf.data[0].shape[0] == data.number_of('chan')[0]
    assert tf.data[0].shape[2] == data.s_freq / 2 + 1
    x = tf(trial=0, chan='LMF6', time=tf.axis['time'][0][10])
    assert_almost_equal(x[0], 5.0586684531420154)
