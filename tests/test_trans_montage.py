from collections import OrderedDict
from numpy import sum, zeros
from numpy.random import seed
from numpy.testing import assert_array_equal, assert_array_almost_equal
from pytest import raises

from wonambi.utils import create_data
from wonambi.trans import montage


seed(0)
data = create_data(attr=['chan', ])


def test_montage_01():
    with raises(TypeError):
        montage(data, ref_chan='chan00')


def test_montage_02():
    reref = montage(data, ref_chan=['chan00'])
    dat1 = reref(chan='chan00')
    assert_array_equal(dat1[0], zeros(dat1[0].shape))


def test_montage_03():
    CHAN = ('chan01', 'chan02')
    reref = montage(data, ref_chan=CHAN)
    dat1 = reref(chan=CHAN)
    assert_array_almost_equal(sum(dat1[0], axis=0), zeros((dat1[0].shape[1])),
                              decimal=6)

def test_montage_04():
    reref = montage(data, ref_chan=[])
    assert_array_equal(data.data[0], reref.data[0])


def test_montage_05():
    with raises(TypeError):
        montage(data, ref_chan=['chan00'], ref_to_avg=True)


def test_montage_06():
    reref = montage(data, ref_to_avg=True)

    dat1 = reref(trial=0)
    assert_array_almost_equal(sum(dat1, axis=0), zeros((dat1.shape[1])),
                              decimal=4)


def test_montage_bipolar_00():
    bipol = montage(data, bipolar=100)

    assert len(bipol.chan[0]) == 28
    assert_array_equal(
        bipol(trial=0, chan='chan00-chan01'),
        data(trial=0, chan='chan00') - data(trial=0, chan='chan01'))


def test_montage_bipolar_01():
    data_nochan = create_data()

    with raises(ValueError):
        montage(data_nochan, bipolar=100)


def test_montage_bipolar_02():
    data_wrongorder = create_data(n_trial=2, attr=['chan', ])
    data_wrongorder.axis['chan'][1] = data_wrongorder.chan[0][-1::-1]

    with raises(ValueError):
        montage(data_wrongorder, bipolar=100)


def test_montage_bipolar_03():
    data_wrongorder = create_data(attr=['chan', ])

    # you should get an error if chan is not first
    data_wrongorder.axis = OrderedDict([
        ('time', data_wrongorder.axis['time']),
        ('chan', data_wrongorder.axis['chan']),
        ])

    with raises(ValueError):
        montage(data_wrongorder, bipolar=100)
