from inspect import stack
from logging import getLogger, FileHandler, DEBUG
from os.path import join, basename, splitext
from nose.tools import raises
from subprocess import check_output
from sys import version_info


git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()

log_dir = '/home/gio/tools/phypno/test/log'
log_file = join(log_dir, splitext(basename(__file__))[0] + '_v' +
                str(version_info[0]) + '.log')
lg = getLogger('phypno')
lg.setLevel(DEBUG)
h_lg = FileHandler(log_file, mode='w')
lg.addHandler(h_lg)
lg.info('phypno ver: ' + git_ver)

#-----------------------------------------------------------------------------#
lg.info('Module: ' + __name__)

#-----------------------------------------------------------------------------#
from phypno import Dataset

data_file = '/home/gio/recordings/MG65/eeg/raw/MG65_eeg_sessA_d01_06_39_33'

def test_Dataset_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(data_file)
    assert d.header['s_freq'] == 512.0
    data = d.read_data(chan=['MFD1'], begsam=0, endsam=1)
