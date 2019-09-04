from numpy import isnan

from wonambi import Dataset
from wonambi.dataset import _count_openephys_sessions
from wonambi.ioeeg import openephys
from wonambi.ioeeg.openephys import OpenEphys

from .paths import openephys_dir as filename

openephys.IGNORE_EVENTS = []


def test_openephys_count_sessions():
    assert _count_openephys_sessions(filename) == [1, 2]


def test_openephys_markers():
    d = Dataset(filename, session=1)
    markers = d.read_markers()

    assert len(markers) == 10
    assert markers[0]['name'] == 'START RECORDING #0'
    assert markers[7]['name'] == 'Network Event'
    assert markers[7]['end'] == 95.402
    assert markers[-1]['name'] == 'END RECORDING #1'


def test_openephys_header():
    self = OpenEphys(filename, session=2)
    subj_id, start_time, s_freq, chan_name, n_samples, orig = self.return_hdr()

    assert start_time.second == 50
    assert len(chan_name) == 19  # some channels were deleted on purpose
    assert n_samples == 262656


def test_openephys_read():
    self = OpenEphys(filename, session=2)
    n_samples = self.return_hdr()[4]
    mrks = self.return_markers()

    # before beginning
    dat = self.return_dat([0, ], -20, -10)
    assert isnan(dat[0, :]).all()

    # beginning
    dat = self.return_dat([0, ], -5, 5)
    assert isnan(dat[0, :5]).all()
    assert not isnan(dat[0, 5:]).any()

    # values
    dat = self.return_dat([0, ], 60021, 60032)
    assert dat[0, :].sum() == -57195.255

    # end of first segment
    start_seg = [x['start'] for x in mrks if x['name'] == 'END RECORDING #0'][0]
    ref = int(start_seg * self.s_freq)

    dat = self.return_dat([0, ], ref - 5, ref + 5)
    assert not isnan(dat[0, :5]).any()
    assert isnan(dat[0, 5:]).all()

    # beginning of second segment
    start_seg = [x['start'] for x in mrks if x['name'] == 'START RECORDING #1'][0]
    ref = int(start_seg * self.s_freq)

    dat = self.return_dat([0, ], ref - 5, ref + 5)
    assert isnan(dat[0, :5]).all()
    assert not isnan(dat[0, 5:]).any()

    # end
    dat = self.return_dat([0, ], n_samples - 5, n_samples + 5)
    assert not isnan(dat[0, :5]).any()
    assert isnan(dat[0, 5:]).all()

    # after end
    dat = self.return_dat([0, ], n_samples, n_samples + 10)
    assert isnan(dat[0, :]).all()
