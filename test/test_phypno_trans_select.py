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

from phypno import Dataset
from phypno.trans import Select

edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(['LOF4', 'LOF5'], begtime=0, endtime=5)


def test_select_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    s = Select(chan=['LOF4'])
    data1 = s(data)
    assert data1.chan_name == ['LOF4']
    assert data1.data.shape[0] == 1


def test_select_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    s = Select(chan=[])
    data1 = s(data)
    assert len(data1.chan_name) == 0
    assert data1.data.shape[0] == 0