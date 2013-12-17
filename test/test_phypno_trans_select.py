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
from phypno.trans import Select


ktlx_dir = '/home/gio/recordings/MG65/eeg/raw/MG65_eeg_sessA_d01_06_39_33'
d = Dataset(ktlx_dir)
data = d.read_data(['GR9', 'GR10'], begtime=0, endtime=5)


def test_select_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    s = Select(chan=['GR9'])
    data1 = s(data)
    assert data1.chan_name == ['GR9']
    assert data1.data.shape[0] == 1
