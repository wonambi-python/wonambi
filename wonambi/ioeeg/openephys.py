from datetime import datetime
from logging import getLogger
from struct import unpack, calcsize
from xml.etree import ElementTree

from numpy import array, ones, empty, NaN

from .edf import _select_blocks

lg = getLogger(__name__)


HDR_LENGTH = 1024
BLK_LENGTH = 1024
BEG_BLK = '<qHH'
DAT_FMT = '>' + BLK_LENGTH * 'h'  # big-endian
END_BLK = 10 * 'B'

BEG_BLK_SIZE = calcsize(BEG_BLK)
DAT_FMT_SIZE = calcsize(DAT_FMT)
BLK_SIZE = BEG_BLK_SIZE + DAT_FMT_SIZE + calcsize(END_BLK)


class OpenEphys:
    def __init__(self, filename):
        self.filename = filename.resolve()
        self.openephys_file = filename / 'Continuous_Data.openephys'
        self.settings_xml = filename / 'settings.xml'

    def return_hdr(self):
        subj_id = self.filename.stem  # use directory name as subject name

        start_time = _read_date(self.settings_xml)

        s_freq, channels = _read_openephys(self.openephys_file)

        # only use channels that are actually in the folder
        chan_name = []
        self.channels = []
        gain = []
        for chan in channels:
            channel_filename = (self.filename / chan['filename'])
            if channel_filename.exists():
                chan_name.append(chan['name'])
                self.channels.append(channel_filename)
                gain.append(_check_header(channel_filename, s_freq))

            else:
                lg.warning(f'could not find {chan["filename"]} in {self.filename}')

        self.gain = array(gain)
        n_blocks, n_samples = _read_n_samples(self.channels[0])

        self.blocks = ones(n_blocks, dtype='int') * BLK_LENGTH

        orig = {}

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

    def return_dat(self, chan, begsam, endsam):

        dat = empty((len(chan), endsam - begsam))
        dat.fill(NaN)
        for i_chan, sel_chan in enumerate(chan):
            with self.channels[sel_chan].open('rb') as f:
                for i_dat, blk, i_blk in _select_blocks(self.blocks, begsam, endsam):
                    dat_in_rec = _read_record_continuous(f, blk)
                    dat[i_chan, i_dat[0]:i_dat[1]] = dat_in_rec[i_blk[0]:i_blk[1]]

        return dat * self.gain[chan, None]

    def return_markers(self):
        """
        TODO
        ----
        read markers from openephys
        """
        return []


def _read_record_continuous(f, i_block):

    f.seek(HDR_LENGTH + i_block * BLK_SIZE + BEG_BLK_SIZE)
    v = unpack(DAT_FMT, f.read(DAT_FMT_SIZE))

    return array(v)


def _read_openephys(openephys_file):

    root = ElementTree.parse(openephys_file).getroot()

    channels = []
    for recording in root:
        s_freq = float(recording.attrib['samplerate'])
        for processor in recording:
            for channel in processor:
                channels.append(channel.attrib)

    return s_freq, channels


def _read_date(settings_file):
    root = ElementTree.parse(settings_file).getroot()
    for e0 in root:
        if e0.tag == 'INFO':
            for e1 in e0:
                if e1.tag == 'DATE':
                    break

    return datetime.strptime(e1.text, '%d %b %Y %H:%M:%S')


def _read_n_samples(channel_file):
    n_blocks = int((channel_file.stat().st_size - HDR_LENGTH) / BLK_SIZE)
    n_samples = n_blocks * BLK_LENGTH
    return n_blocks, n_samples


def _read_header(filename):
    with filename.open('rb') as f:
        h = f.read(HDR_LENGTH).decode()

        header = {}
        for line in h.split('\n'):
            if '=' in line:
                key, value = line.split(' = ')
                key = key.strip()[7:]
                value = value.strip()[:-1]
                header[key] = value

    return header


def _check_header(channel_file, s_freq):
    """For each file, make sure that the header is consistent
    """
    hdr = _read_header(channel_file)

    assert int(hdr['header_bytes']) == HDR_LENGTH
    assert int(hdr['blockLength']) == BLK_LENGTH
    assert int(hdr['sampleRate']) == s_freq

    return float(hdr['bitVolts'])
