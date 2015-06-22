from os.path import abspath, join
from numpy.testing import assert_array_equal

from numpy import arange, array, empty, isnan, where
from numpy.random import random

from phypno import Data, Dataset, ChanTime, ChanTimeFreq
from phypno.utils import create_data

import phypno
data_dir = abspath(join(phypno.__path__[0], '..', 'data'))


def test_data_select_trial():
    data = create_data(n_trial=10, s_freq=500)

    output = data(trial=(1, 2, 3))
    assert len(output) == 3


def test_data_select_trial_compress():
    data = create_data(n_trial=10, s_freq=500)

    output = data(trial=(1, ))
    assert len(output) == 1

    output = data(trial=1)
    assert output.shape == (data.number_of('chan')[0],
                            data.number_of('time')[0])

    output = data(trial=(1, 2), squeeze=True)
    assert len(output) == 2


def test_data_select_one_axis():
    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][:10]
    output = data(time=TIME)
    assert len(output) == 10
    assert output[0].shape[data.index_of('time')] == len(TIME)


def test_data_select_two_axis():
    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][:10]
    CHAN = ('chan02', 'chan05')
    output = data(chan=CHAN, time=TIME)
    assert len(output) == 10
    assert output[0].shape == (len(CHAN), len(TIME))


def test_data_select_one_value():
    data = create_data(n_trial=10, s_freq=500)

    TIME = data.axis['time'][0][0]
    output = data(time=TIME)
    assert len(output) == 10
    assert output[0].ndim == 1

    output = data(trial=1, time=TIME)
    assert output.ndim == 1


def test_data_select_one_value_twice():
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
    data = create_data(n_trial=10, s_freq=500)

    TIME = (100, 200)
    CHAN = ('chan02', 'chan05')
    output = data(chan=CHAN, time=TIME)
    assert output[0].shape == (len(CHAN), len(TIME))
    assert isnan(output[0][:]).all()


def test_data_select_one_empty_selection():
    data = create_data(n_trial=10, s_freq=500)

    CHAN = 'chanXX'
    output = data(chan=CHAN, trial=0)
    assert output.shape == (data.number_of('time')[0], )
    assert isnan(output[:]).all()


def test_data_conserve_order():
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
    data = create_data(n_trial=10, s_freq=500)

    TIME = arange(0, 1, 0.05)
    output = data(time=TIME)
    assert len(where(isnan(output[0][0, :]))[0]) == 4  # without tolerance

    TIME = arange(0, 1, 0.05)
    CHAN = ('chan02', 'chan05')
    output = data(time=TIME, chan=CHAN, tolerance=1e-10)
    assert len(where(isnan(output[0][0, :]))[0]) == 0


def test_data_arbitrary_axis():
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
    data = create_data(n_trial=10, s_freq=500)

    from phypno.trans import Math

    for one_trial in iter(data):
        take_mean = Math(operator_name='mean', axis='time')
        one_mean = take_mean(one_trial)


def test_datatype_with_freq():
    ChanTime()
    ChanTimeFreq()

edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LOF1', 'LOF2', 'LMF6'], begtime=0, endtime=60)


def test_chantime_realdata():
    chan_limits = ['LOF1', 'LOF2']
    sel_dat = data(chan=chan_limits)
    assert sel_dat[0].shape[0] == 2


def test_chantime_select_equal_to_read():
    subdata = d.read_data(chan=['LOF1', 'LOF2'], begtime=0, endtime=1)
    dat1 = subdata()

    TIME = data.axis['time'][0][data.axis['time'][0] < 1]
    dat2 = data(chan=['LOF1', 'LOF2'], time=TIME)

    assert_array_equal(dat1[0], dat2[0])


def test_data_one_dim_one_value():
    data = Data()
    data.axis = {'chan': empty(1, dtype='O')}
    data.axis['chan'][0] = array(('chan02', 'chan05'))
    data.data = empty(1, dtype='O')
    data.data[0] = array((10, 20))
    assert data(trial=0, chan='chan02') == 10
