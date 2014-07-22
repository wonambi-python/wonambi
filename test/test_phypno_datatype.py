from . import *

from os.path import join

from numpy import arange, array, empty, isnan, where
from numpy.random import random

from phypno import Data, Dataset, ChanTime, ChanTimeFreq
from phypno.utils import create_data


def test_data_select_trial():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    output = data(trial=(1, 2, 3))
    assert len(output) == 3


def test_data_select_trial_compress():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    output = data(trial=(1, ))
    assert len(output) == 1

    output = data(trial=1)
    assert output.shape == (data.number_of('chan')[0],
                            data.number_of('time')[0])

    output = data(trial=(1, 2), squeeze=True)
    assert len(output) == 2


def test_data_select_one_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][:10]
    output = data(time=TIME)
    assert len(output) == 10
    assert output[0].shape[data.index_of('time')] == len(TIME)


def test_data_select_two_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][:10]
    CHAN = ('chan02', 'chan05')
    output = data(chan=CHAN, time=TIME)
    assert len(output) == 10
    assert output[0].shape == (len(CHAN), len(TIME))


def test_data_select_one_value():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][0]
    output = data(time=TIME)
    assert len(output) == 10
    assert output[0].ndim == 1

    output = data(trial=1, time=TIME)
    assert output.ndim == 1


def test_data_select_one_value_twice():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][0]
    CHAN = ('chan02', )
    output = data(time=TIME, chan=CHAN)
    assert len(output) == 10
    assert output[0].ndim == 1

    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][0]
    CHAN = 'chan02'
    output = data(time=TIME, chan=CHAN)
    assert len(output) == 10
    assert output[0].ndim == 0


def test_data_select_empty_selection():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    TIME = (100, 200)
    CHAN = ('chan02', 'chan05')
    output = data(chan=CHAN, time=TIME)
    assert output[0].shape == (len(CHAN), len(TIME))
    assert isnan(output[0][:]).all()


def test_data_select_one_empty_selection():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    CHAN = 'chanXX'
    output = data(chan=CHAN, trial=0)
    assert output.shape == (data.number_of('time')[0], )
    assert isnan(output[:]).all()


def test_data_conserve_order():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    CHAN = ('chan02', )
    output02 = data(chan=CHAN, trial=0)

    CHAN = ('chan05', )
    output05 = data(chan=CHAN, trial=0)

    CHAN = ('chan02', 'chan02')
    output0202 = data(chan=CHAN, trial=0)

    CHAN = ('chan05', 'chan02')
    output0502 = data(chan=CHAN, trial=0)

    assert_array_equal(output02[0, :10], output0202[0, :10])
    assert_array_equal(output0502[0, :10], output05[0, :10])
    assert_array_equal(output0502[1, :10], output02[0, :10])


def test_data_select_tolerance():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    TIME = arange(0, 1, 0.05)
    output = data(time=TIME)
    assert len(where(isnan(output[0][0, :]))[0]) == 4  # without tolerance

    TIME = arange(0, 1, 0.05)
    CHAN = ('chan02', 'chan05')
    output = data(time=TIME, chan=CHAN, tolerance=1e-10)
    assert len(where(isnan(output[0][0, :]))[0]) == 0


def test_data_arbitrary_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = Data()
    len_axis0 = 6
    data.axis['axis0'] = empty(1, dtype='O')
    data.axis['axis0'][0] = array(['x' + str(x) for x in range(len_axis0)],
                                dtype='U')
    len_axis1 = 10
    data.axis['axis1'] = empty(1, dtype='O')
    data.axis['axis1'][0] = arange(len_axis1)
    len_axis2 = 10
    data.axis['axis2'] = empty(1, dtype='O')
    data.axis['axis2'][0] = arange(len_axis2)
    len_axis3 = 5
    data.axis['axis3'] = empty(1, dtype='O')
    data.axis['axis3'][0] = arange(len_axis3)

    data.data = empty(1, dtype='O')
    data.data[0] = random((len_axis0, len_axis1, len_axis2, len_axis3))

    output = data(axis0=('x0', 'x3', 'x2'), axis1=(4, 6), axis2=(8, 1),
                  axis3=(0, 1, 2))
    assert output[0].shape == (3, 2, 2, 3)


def test_iter_trials():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10, s_freq=500)

    from phypno.trans import Math

    for one_trial in iter(data):
        take_mean = Math(operator_name='mean', axis='time')
        one_mean = take_mean(one_trial)


def test_datatype_with_freq():
    lg.info('---\nfunction: ' + stack()[0][3])

    ChanTime()
    ChanTimeFreq()

edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LOF1', 'LOF2', 'LMF6'], begtime=0, endtime=60)


def test_chantime_realdata():
    lg.info('---\nfunction: ' + stack()[0][3])

    chan_limits = ['LOF1', 'LOF2']
    sel_dat = data(chan=chan_limits)
    assert sel_dat[0].shape[0] == 2


def test_chantime_select_equal_to_read():
    lg.info('---\nfunction: ' + stack()[0][3])

    subdata = d.read_data(chan=['LOF1', 'LOF2'], begtime=0, endtime=1)
    dat1 = subdata()

    TIME = data.axis['time'][0][data.axis['time'][0] < 1]
    dat2 = data(chan=['LOF1', 'LOF2'], time=TIME)

    assert_array_equal(dat1[0], dat2[0])

"""
TODO
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

    time_limits = (4, 5)
    freq_limits = (10, 25)
    sel_dat, sel_time, sel_freq = tf(freq=freq_limits, time=time_limits)
    assert sel_dat[0].shape[0] == 3
    assert sel_time[0].shape[0] == 1
    assert sel_dat[0].shape[2] == 15

"""
