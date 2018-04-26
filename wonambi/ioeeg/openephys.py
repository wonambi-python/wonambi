"""Module to read open-ephys .continuous files

TODO
----
It assumes that the lenght of a block (i.e. record) is 1024 data points but this
might change in the future.
"""
from datetime import datetime
from logging import getLogger
from struct import unpack, calcsize
from xml.etree import ElementTree

from numpy import array, ones, empty, NaN

from .edf import _select_blocks

lg = getLogger(__name__)


HDR_LENGTH = 1024  # this is fixed
BLK_LENGTH = 1024  # this is currently fixed but might change in the future
BEG_BLK = '<qHH'  # time information and indices
DAT_FMT = '>' + BLK_LENGTH * 'h'  # actual data, big-endian
END_BLK = 10 * 'B'  # control values

BEG_BLK_SIZE = calcsize(BEG_BLK)
DAT_FMT_SIZE = calcsize(DAT_FMT)
BLK_SIZE = BEG_BLK_SIZE + DAT_FMT_SIZE + calcsize(END_BLK)


class OpenEphys:
    """Provide class OpenEphys, which can be used to read the folder
    containing Open-Ephys .continuous files

    Parameters
    ----------
    filename : Path
        Full path for the EDF file

    Attributes
    ----------
    channels : list of dict
        list of filenames referring to channels which are actually on disk
    blocks : 1D array
        length of each block, in samples (currently 1024)
    gain : 1D array
        gain to convert digital to microvolts (one value per channel)
    """
    def __init__(self, filename):
        self.filename = filename.resolve()
        self.openephys_file = filename / 'Continuous_Data.openephys'
        self.settings_xml = filename / 'settings.xml'

    def return_hdr(self):
        """Return the header for further use.

        Returns
        -------
        subj_id : str
            subject identification code
        start_time : datetime
            start time of the dataset
        s_freq : float
            sampling frequency
        chan_name : list of str
            list of all the channels
        n_samples : int
            number of samples in the dataset
        orig : dict
            currently empty for open-ephys
        """
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
        """Read the data for some/all of the channels

        Parameters
        ----------
        chan : list of int
            indices of the channels to read
        begsam : int
            start sample to read
        endsam : int
            end sample to read (exclusive)

        Returns
        -------
        2D array
            chan X samples recordings
        """
        dat = empty((len(chan), endsam - begsam))
        dat.fill(NaN)

        for i_chan, sel_chan in enumerate(chan):
            with self.channels[sel_chan].open('rb') as f:
                for i_dat, blk, i_blk in _select_blocks(self.blocks, begsam, endsam):
                    dat_in_rec = _read_block_continuous(f, blk)
                    dat[i_chan, i_dat[0]:i_dat[1]] = dat_in_rec[i_blk[0]:i_blk[1]]

        return dat * self.gain[chan, None]

    def return_markers(self):
        """Read the markers from the .events file

        TODO
        ----
        read markers from openephys
        """
        return []


def _read_block_continuous(f, i_block):
    """Read a single block / record completely

    Parameters
    ----------
    f : file handle
        handle to a file opened with 'rb'
    i_block : int
        index of the block to read

    Returns
    -------
    1D array
        data inside a block for one channel

    Notes
    -----
    It skips the timestamp information (it's assumed to be continuous) and the
    control characters. Maybe it might be useful to check the control
    characters but it will slow down the execution.
    """
    f.seek(HDR_LENGTH + i_block * BLK_SIZE + BEG_BLK_SIZE)
    v = unpack(DAT_FMT, f.read(DAT_FMT_SIZE))

    return array(v)


def _read_openephys(openephys_file):
    """Read the channel labels and their respective files from the
    'Continuous_Data.openephys' file

    Parameters
    ----------
    openephys_file : Path
        path to Continuous_Data.openephys inside the open-ephys folder

    Returns
    -------
    int
        sampling frequency
    list of dict
        list of channels containing the label, the filename and the gain
    """
    root = ElementTree.parse(openephys_file).getroot()

    channels = []
    for recording in root:
        s_freq = float(recording.attrib['samplerate'])
        for processor in recording:
            for channel in processor:
                channels.append(channel.attrib)

    return s_freq, channels


def _read_date(settings_file):
    """Get the data from the settings.xml file

    Parameters
    ----------
    settings_file : Path
        path to settings.xml inside open-ephys folder

    Returns
    -------
    datetime
        start time of the recordings

    Notes
    -----
    The start time is present in the header of each file. This might be useful
    if 'settings.xml' is not present.
    """
    root = ElementTree.parse(settings_file).getroot()
    for e0 in root:
        if e0.tag == 'INFO':
            for e1 in e0:
                if e1.tag == 'DATE':
                    break

    return datetime.strptime(e1.text, '%d %b %Y %H:%M:%S')


def _read_n_samples(channel_file):
    """Calculate the number of samples based on the file size

    Parameters
    ----------
    channel_file : Path
        path to single filename with the header

    Returns
    -------
    int
        number of blocks (i.e. records, in which the data is cut)
    int
        number of samples
    """
    n_blocks = int((channel_file.stat().st_size - HDR_LENGTH) / BLK_SIZE)
    n_samples = n_blocks * BLK_LENGTH
    return n_blocks, n_samples


def _read_header(filename):
    """Read the text header for each file

    Parameters
    ----------
    channel_file : Path
        path to single filename with the header

    Returns
    -------
    dict
        header
    """
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
    """For each file, make sure that the header is consistent with the
    information in the text file.

    Parameters
    ----------
    channel_file : Path
        path to single filename with the header
    s_freq : int
        sampling frequency

    Returns
    -------
    int
        gain from digital to microvolts (the same information is stored in
        the Continuous_Data.openephys but I trust the header for each file more.
    """
    hdr = _read_header(channel_file)

    assert int(hdr['header_bytes']) == HDR_LENGTH
    assert int(hdr['blockLength']) == BLK_LENGTH
    assert int(hdr['sampleRate']) == s_freq

    return float(hdr['bitVolts'])
