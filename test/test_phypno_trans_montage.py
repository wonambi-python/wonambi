from . import *

from os.path import join

from numpy import sum, zeros
from numpy.testing import assert_array_equal, assert_array_almost_equal

from phypno.utils import create_data
from phypno.trans import Montage

data = create_data(n_trial=10)


@raises(TypeError)
def test_montage_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    Montage(ref_chan='LMF5')


def test_montage_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    make_reref = Montage(ref_chan=['LMF5'])
    reref = make_reref(data)
    dat1 = reref(chan=['LMF5'])
    assert_array_equal(dat1[0], zeros(dat1[0].shape))


def test_montage_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    make_reref = Montage(ref_chan=['LMF5', 'LMF6'])
    reref = make_reref(data)
    dat1 = reref()
    assert_array_almost_equal(sum(dat1[0], axis=0), zeros((dat1[0].shape[1])),
                              decimal=4)


def test_montage_04():
    lg.info('---\nfunction: ' + stack()[0][3])

    make_reref = Montage(ref_chan=[])
    reref = make_reref(data)
    dat1, _ = reref()
    assert id(data) != id(reref)  # test deepcopy
    assert_array_equal(data.data[0], reref.data[0])


@raises(TypeError)
def test_montage_05():
    lg.info('---\nfunction: ' + stack()[0][3])

    Montage(ref_chan=['LMF5'], ref_to_avg=True)


def test_montage_06():
    lg.info('---\nfunction: ' + stack()[0][3])

    make_reref = Montage(ref_to_avg=True)
    reref = make_reref(data)
    dat1, _ = reref()
    assert_array_almost_equal(sum(dat1[0], axis=0), zeros((dat1[0].shape[1])),
                              decimal=4)
