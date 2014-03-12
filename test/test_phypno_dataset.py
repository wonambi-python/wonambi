from inspect import stack
from logging import getLogger, INFO
from nose.tools import raises
from numpy.testing import assert_array_equal
from subprocess import check_output


lg = getLogger('phypno')
lg.setLevel(INFO)
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

data_dir = '/home/gio/tools/phypno/data'

#-----------------------------------------------------------------------------#
from os.path import join
from datetime import timedelta, datetime
from numpy.random import rand
from phypno import Dataset
from phypno.utils.exceptions import UnrecognizedFormat

empty_file = join(data_dir, 'MGXX/eeg/raw/blackrock/neuroport/empty_file')
empty_dir = join(data_dir, 'MGXX/eeg/raw/xltek/empty_dir')
ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
blackrock_file = join(data_dir, 'MGXX/eeg/raw/blackrock/neuroport',
                      'MGXX_eeg_neuroport_sessA_d00_14_14_30.ns5')
nev_file = join(data_dir, 'MGXX/eeg/raw/blackrock/neuroport',
                          'MGXX_eeg_neuroport_sessA_d00_14_14_30.nev')


@raises(UnrecognizedFormat)
def test_Dataset_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    Dataset(empty_file)


@raises(UnrecognizedFormat)
def test_Dataset_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    Dataset(empty_dir)


class IOEEG:
    def __init__(self, filename):
        self.filename = filename

    def return_hdr(self):
        return str(), datetime.now(), 1, ['0', '1'], 1, dict()

    def return_dat(self, chan, begsam, endsam):
        data = rand(10, 100)
        return data[chan, begsam:endsam]


def test_Dataset_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(empty_dir, IOClass=IOEEG)
    d.read_data(begsam=0, endsam=1)


def test_Dataset_04():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(ktlx_dir)
    assert d.header['s_freq'] == 512.0
    d.read_data(chan=['MFD1'], begsam=0, endsam=1)
    dat0 = d.read_data(chan=['MFD1'], begtime=0, endtime=1)
    dat1 = d.read_data(chan=['MFD1'], begtime=0, endtime=1)  # caching
    assert_array_equal(dat0.data, dat1.data)


def test_Dataset_05():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(ktlx_dir)
    assert d.header['s_freq'] == 512.0
    d.read_data(chan=['MFD1'], begsam=0, endsam=1)
    d.read_data(chan=['MFD1'], begtime=0, endtime=1)
    d.read_data(chan=['MFD1'], begtime=datetime(2013, 4, 5, 6, 39, 33),
                endtime=datetime(2013, 4, 5, 6, 49, 34))
    d.read_data(chan=['MFD1'], begtime=timedelta(seconds=1),
                endtime=timedelta(seconds=2))


def test_Dataset_06():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(edf_file)
    d.read_data(begsam=0, endsam=1)
    d.read_data(chan=['LMF6'], begsam=0, endsam=1)


@raises(TypeError)
def test_Dataset_07():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(edf_file)
    d.read_data(chan='aaa', begsam=0, endsam=1)


def test_Dataset_08():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(blackrock_file)
    d.read_data(chan=['chan1'], begsam=0, endsam=2)


def test_Dataset_09():
    lg.info('---\nfunction: ' + stack()[0][3])
    Dataset(nev_file)
