from inspect import stack
from logging import getLogger
from nose.tools import raises
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

data_dir = '/home/gio/tools/phypno/data'

#-----------------------------------------------------------------------------#
from os.path import join

from numpy import sum, zeros
from numpy.testing import assert_array_equal, assert_array_almost_equal

from phypno import Dataset
from phypno.trans import Montage


edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LMF5', 'LMF6'], begtime=0, endtime=100)


@raises(TypeError)
def test_montage_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    Montage(ref_chan='LMF5')


def test_montage_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    make_reref = Montage(ref_chan=['LMF5'])
    reref = make_reref(data)
    dat1, _ = reref(chan=['LMF5'])
    assert_array_equal(dat1, zeros(dat1.shape))


def test_montage_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    make_reref = Montage(ref_chan=['LMF5', 'LMF6'])
    reref = make_reref(data)
    dat1, _ = reref()
    assert_array_almost_equal(sum(dat1, axis=0), zeros((dat1.shape[1])),
                              decimal=4)


def test_montage_04():
    lg.info('---\nfunction: ' + stack()[0][3])
    make_reref = Montage(ref_chan=[])
    reref = make_reref(data)
    dat1, _ = reref()
    assert id(data) != id(reref)  # test deepcopy
    assert_array_equal(data.data, reref.data)


@raises(TypeError)
def test_montage_05():
    lg.info('---\nfunction: ' + stack()[0][3])
    Montage(ref_chan=['LMF5'], ref_to_avg=True)


def test_montage_06():
    lg.info('---\nfunction: ' + stack()[0][3])
    make_reref = Montage(ref_to_avg=True)
    reref = make_reref(data)
    dat1, _ = reref()
    assert_array_almost_equal(sum(dat1, axis=0), zeros((dat1.shape[1])),
                              decimal=4)
