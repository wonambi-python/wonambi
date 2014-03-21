from inspect import stack
from logging import getLogger
from nose.tools import raises
from numpy.testing import assert_array_equal
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

from phypno import Dataset
from phypno.trans import Select
from phypno.utils import create_data

edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(['LOF4', 'LOF5'], begtime=0, endtime=5)


def test_select_trial():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(trial=(0, 0))
    data1 = s(data)
    assert_array_equal(data1.data[0], data1.data[1])
    assert len(data1.axis['chan']) == 2
    assert len(data1.axis['time']) == 2


def test_select_string_selection():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(chan=['LOF4'])
    data1 = s(data)
    assert data1.axis['chan'][0][0] == 'LOF4'
    assert data1.data[0].shape[0] == 1


def test_select_empty_selection():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(chan=[])
    data1 = s(data)
    assert len(data1.axis['chan'][0]) == 0
    assert data1.data[0].shape[0] == 0


data = create_data(n_trial=10)


def test_select_trials():
    lg.info('---\nfunction: ' + stack()[0][3])

    s = Select(trial=(1, 5))
    data1 = s(data)
    assert_array_equal(data.data[1], data1.data[0])


def test_select_trials_and_string():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(n_trial=10)
    s = Select(trial=(1, 5), chan=('chan01', 'chan02'))
    data1 = s(data)
    assert len(data1.axis['chan']) == 2
    assert len(data1.axis['chan'][0]) == 2
