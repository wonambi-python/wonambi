from . import *

from numpy import arange, pi, sin

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


@raises(ValueError)
def test_timefreq_methoderror():
    lg.info('---\nfunction: ' + stack()[0][3])

    TimeFreq(method='nonexistent')


@raises(ValueError)
def test_timefreq_no_foi():
    lg.info('---\nfunction: ' + stack()[0][3])

    TimeFreq()


def test_timefreq_basic():
    lg.info('---\nfunction: ' + stack()[0][3])

    FOI = arange(5, 10)
    calc_tf = TimeFreq(foi=FOI)
    tf = calc_tf(data)

    assert tf.list_of_axes == ('chan', 'time', 'freq')
    assert tf.data[0].shape[0] == data.number_of('chan')[0]
    assert tf.data[0].shape[1] == data.number_of('time')[0]
    assert tf.data[0].shape[2] == len(FOI)
    x = tf(trial=0, chan='LMF6', time=tf.axis['time'][0][10])
    assert_array_equal(x[0], (-2044.061426326871+1949.3118007336147j))


def test_timefreq_example_in_doc():
    lg.info('---\nfunction: ' + stack()[0][3])

    from phypno.trans import Math, TimeFreq
    calc_tf = TimeFreq(foi=(8, 10))
    tf = calc_tf(data)
    make_abs = Math(operator_name='abs')
    tf_abs = make_abs(tf)
    assert_array_equal(tf_abs.data[0][0, 0, 0], 1737.4662329214384)


def test_timefreq_sine():
    lg.info('---\nfunction: ' + stack()[0][3])

    FREQ = 10
    data = create_data(n_chan = 1)
    data.data[0][0,:] = sin(2 * pi * data.axis['time'][0] * FREQ)

    FOI = arange(4, 20)
    calc_tf = TimeFreq(foi=FOI)
    tf = calc_tf(data)
    make_abs = Math(operator_name='abs')
    tf_abs = make_abs(tf)
    x = tf_abs(trial=0, chan='chan00')

    # peak in power spectrum is where the frequency of the sine wave
    assert FOI[x[200, :].argmax()] == FREQ
