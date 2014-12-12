from . import *

from datetime import timedelta, datetime
from numpy import float64, int64
from numpy.random import rand

from phypno import Dataset
from phypno.dataset import _convert_time_to_sample
from phypno.utils.exceptions import UnrecognizedFormat

empty_file = join(data_dir, 'MGXX/eeg/raw/blackrock/neuroport/empty_file')
empty_dir = join(data_dir, 'MGXX/eeg/raw/xltek/empty_dir')
ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
blackrock_file = join(data_dir, 'MGXX/eeg/raw/blackrock/neuroport',
                      'MG72_eeg_bcd_sessA_d11_11_49_17.ns3')
nev_file = join(data_dir, 'MGXX/eeg/raw/blackrock/neuroport',
                          'MG72_eeg_bcd_sessA_d11_11_49_17.nev')


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
    dat0 = d.read_data(chan=['MFD1'], begtime=10, endtime=11)
    dat1 = d.read_data(chan=['MFD1'], begtime=10, endtime=11)  # caching
    assert_array_equal(dat0.data[0], dat1.data[0])


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
    d = Dataset(ktlx_dir)
    d.read_data(chan=['MFD1'], begsam=[0, 10], endsam=[1, 11])
    d.read_data(chan=['MFD1'],
                begtime=[datetime(2013, 4, 5, 6, 39, 33),
                         datetime(2013, 4, 5, 6, 40, 33)],
                endtime=[datetime(2013, 4, 5, 6, 39, 43),
                         datetime(2013, 4, 5, 6, 40, 53)])


@raises(ValueError)
def test_Dataset_07():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(ktlx_dir)
    d.read_data(chan=['MFD1'], begsam=[0, 10], endsam=11)


def test_Dataset_08():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(edf_file)
    d.read_data(begsam=0, endsam=1)
    d.read_data(chan=['LMF6'], begsam=0, endsam=1)


@raises(TypeError)
def test_Dataset_09():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(edf_file)
    d.read_data(chan='aaa', begsam=0, endsam=1)


def test_Dataset_10():
    lg.info('---\nfunction: ' + stack()[0][3])
    d = Dataset(blackrock_file)
    d.read_data(chan=['chan1'], begsam=0, endsam=2)


def test_Dataset_11():
    lg.info('---\nfunction: ' + stack()[0][3])
    Dataset(nev_file)


d = Dataset(empty_dir, IOClass=IOEEG)
TIME_DIFF = 10


def test_convert_time_to_sample_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    time1 = d.header['start_time'] + timedelta(seconds=TIME_DIFF)
    assert _convert_time_to_sample(time1, d) == TIME_DIFF


def test_convert_time_to_sample_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    time1 = timedelta(seconds=TIME_DIFF)
    assert _convert_time_to_sample(time1, d) == TIME_DIFF


def test_convert_time_to_sample_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    time1 = int(TIME_DIFF)
    assert _convert_time_to_sample(time1, d) == TIME_DIFF


def test_convert_time_to_sample_04():
    lg.info('---\nfunction: ' + stack()[0][3])
    time1 = float(TIME_DIFF)
    assert _convert_time_to_sample(time1, d) == TIME_DIFF


def test_convert_time_to_sample_05():
    lg.info('---\nfunction: ' + stack()[0][3])
    time1 = float64(TIME_DIFF)
    assert _convert_time_to_sample(time1, d) == TIME_DIFF


def test_convert_time_to_sample_06():
    lg.info('---\nfunction: ' + stack()[0][3])
    time1 = int64(TIME_DIFF)
    assert _convert_time_to_sample(time1, d) == TIME_DIFF


@raises(TypeError)
def test_convert_time_to_sample_07():
    lg.info('---\nfunction: ' + stack()[0][3])
    time1 = str(TIME_DIFF)
    assert _convert_time_to_sample(time1, d) == TIME_DIFF
