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
from phypno.utils.exceptions import UnrecognizedFormat

empty_file = '/home/gio/tools/phypno/test/data/empty'
empty_dir = '/home/gio/tools/phypno/test/data/emptydir'
ktlx_dir = '/home/gio/recordings/MG65/eeg/raw/MG65_eeg_sessA_d01_06_39_33'
edf_file = '/home/gio/tools/phypno/test/data/sample.edf'


@raises(UnrecognizedFormat)
def test_Dataset_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    Dataset(empty_file)


@raises(UnrecognizedFormat)
def test_Dataset_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    Dataset(empty_dir)


def test_Dataset_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(ktlx_dir)
    assert d.header['s_freq'] == 512.0
    d.read_data(chan=['MFD1'], begsam=0, endsam=1)
    d.read_data(chan=['MFD1'], begtime=0, endtime=1)
    d.read_data(chan=['MFD1'], begtime=datetime(2013, 4, 3, 6, 39, 33),
                endtime=datetime(2013, 4, 3, 7, 9, 34))
    d.read_data(chan=['MFD1'], begtime=timedelta(seconds=1),
                endtime=timedelta(seconds=2))


def test_Dataset_04():
    d = Dataset(edf_file)
    d.read_data(begsam=0, endsam=1)
    d.read_data(chan=['LMF6'], begsam=0, endsam=1)
    d.read_data(chan=['LMF6'], ref_chan=['LMF6'], begsam=0, endsam=1)


@raises(ValueError)
def test_Dataset_05():
    d = Dataset(edf_file)
    d.read_data(chan='aaa', begsam=0, endsam=1)
