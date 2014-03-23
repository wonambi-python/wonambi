from . import *

from os.path import join

from phypno import Dataset
from phypno.trans import Filter

edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LMF5', 'LMF6'], begtime=0, endtime=100)


@raises(TypeError)
def test_filter_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter()


def test_filter_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    f = Filter(low_cut=.1)
    f(data)


@raises(ValueError)
def test_filter_wrong_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    f = Filter(low_cut=.1)
    f(data, axis='chan')  # too short


@raises(ValueError)
def test_filter_nonexistent_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    f = Filter(low_cut=.1)
    f(data, axis='xxx')


def test_filter_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter(high_cut=.4)


def test_filter_04():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter(low_cut=.1, high_cut=.4)


def test_filter_05():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter(low_cut=.1, order=5)


def test_filter_06():
    lg.info('---\nfunction: ' + stack()[0][3])

    f1 = Filter(low_cut=10, s_freq=200)
    f2 = Filter(low_cut=.1)
    assert all(f1.a == f2.a)
