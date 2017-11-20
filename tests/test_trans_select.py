from numpy import arange
from numpy.random import seed
from numpy.testing import assert_array_equal
from pytest import raises

from wonambi.utils import create_data
from wonambi.trans import select
from wonambi.trans.select import _create_subepochs


seed(0)
data = create_data(n_trial=5)


def test_select_typeerror():
    with raises(TypeError):
        select(data, trial=1)

    with raises(TypeError):
        select(chan='chan01')

    with raises(TypeError):
        select(data, time=1, chan=('chan01', ))


def test_select_trial():

    data1 = select(data, trial=(1, 2))
    assert data1.number_of('trial') == 2

    data1 = select(data, trial=(0, 0))
    assert_array_equal(data1.data[0], data1.data[1])
    assert len(data1.axis['chan']) == 2
    assert data1.number_of('trial') == 2


def test_select_string_selection():
    data1 = select(data, chan=['chan02'])
    assert data1.axis['chan'][0][0] == 'chan02'
    assert data1.data[0].shape[0] == 1


def test_select_empty_selection():
    data1 = select(data, chan=[])
    assert len(data1.axis['chan'][0]) == 0
    assert data1.data[0].shape[0] == 0


def test_select_create_subepochs():

    # 1d
    x = arange(1000)
    nperseg = 100
    step = 50
    v = _create_subepochs(x, nperseg, step)
    assert v.shape == (19, nperseg)
    assert v[0, step] == v[1, 0]

    # 2d
    x = arange(1000).reshape(20, 50)
    nperseg = 10
    step = 5
    v = _create_subepochs(x, nperseg, step)
    assert v.shape == (20, 9, nperseg)
    assert_array_equal(v[:, 0, step], v[:, 1, 0])

    # 3d
    x = arange(1000).reshape(4, 5, 50)
    v = _create_subepochs(x, nperseg, step)
    assert v.shape == (4, 5, 9, nperseg)
    assert_array_equal(v[..., 0, step], v[..., 1, 0])
