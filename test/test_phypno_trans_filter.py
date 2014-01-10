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

#-----------------------------------------------------------------------------#
from phypno import Dataset
from phypno.trans import Filter

edf_file = '/home/gio/tools/phypno/test/data/sample.edf'
d = Dataset(edf_file)
data = d.read_data(chan=['LMF6'], begtime=0, endtime=100)


@raises(TypeError)
def test_filter_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    f = Filter()


def test_filter_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    f = Filter(low_cut=.1)
    f(data)


def test_filter_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    f = Filter(high_cut=.4)


def test_filter_04():
    lg.info('---\nfunction: ' + stack()[0][3])
    f = Filter(low_cut=.1, high_cut=.4)


def test_filter_05():
    lg.info('---\nfunction: ' + stack()[0][3])
    f = Filter(low_cut=.1, order=5)


def test_filter_06():
    lg.info('---\nfunction: ' + stack()[0][3])
    f1 = Filter(low_cut=10, s_freq=200)
    f2 = Filter(low_cut=.1)
    assert all(f1.a == f2.a)
