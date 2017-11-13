from numpy import arange
from numpy.testing import assert_array_equal

from wonambi.trans.select import _create_subepochs


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