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
from datetime import timedelta, datetime
from phypno import Dataset

data_file = '/home/gio/recordings/MG65/eeg/raw/MG65_eeg_sessA_d01_06_39_33'
edf_file = '/home/gio/tools/phypno/test/data/sample.edf'


def test_Dataset_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(data_file)
    assert d.header['s_freq'] == 512.0
    d.read_data(chan=['MFD1'], begsam=0, endsam=1)
    d.read_data(chan=['MFD1'], begtime=0, endtime=1)
    d.read_data(chan=['MFD1'], begtime=datetime(2013, 4, 3, 6, 39, 33),
                endtime=datetime(2013, 4, 3, 6, 39, 34))
    d.read_data(chan=['MFD1'], begtime=timedelta(seconds=1),
                endtime=timedelta(seconds=2))

def test_Dataset_02():
    d = Dataset(edf_file)
    d.read_data(chan=['LMF6'], begsam=0, endsam=1)
