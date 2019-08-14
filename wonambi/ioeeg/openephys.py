"""Module to read open-ephys .continuous files

TODO
----
It assumes that the lenght of a block (i.e. record) is 1024 data points but this
might change in the future.
"""
from datetime import datetime
from logging import getLogger
import locale
from struct import unpack, calcsize
from math import ceil
from re import search, match
from xml.etree import ElementTree

from numpy import array, empty, NaN, fromfile, unique, where

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
        Full path for the OpenEphys folder
    session : int
        session number (starting at 1, based on open-ephys convention)

    Attributes
    ----------
    channels : list of dict
        list of filenames referring to channels which are actually on disk
    blocks : 1D array
        length of each block, in samples (currently 1024)
    gain : 1D array
        gain to convert digital to microvolts (one value per channel)
    """
    def __init__(self, filename, session=1):

        if session == 1:
            self.session = ''
        else:
            self.session = f'_{session:d}'

        self.filename = filename.resolve()
        self.openephys_file = filename / f'Continuous_Data{self.session}.openephys'
        self.settings_xml = filename / f'settings{self.session}.xml'
        self.messages_file = filename / f'messages{self.session}.events'
        self.events_file = filename / f'all_channels{self.session}.events'

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

        self.recordings = _read_openephys(self.openephys_file)
        s_freq = self.recordings[0]['s_freq']
        self.s_freq = s_freq
        channels = self.recordings[0]['channels']

        segments, messages = _read_messages_events(self.messages_file)
        self.segments = segments
        self.messages = messages
        self.offsets = [int(x['channels'][0]['position']) for x in self.recordings]

        for i in range(len(self.segments) - 1):
            self.segments[i]['length'] = int((self.offsets[i + 1] - self.offsets[0]) / BLK_SIZE * BLK_LENGTH)
            self.segments[i]['data_offset'] = self.offsets[i]

        self.segments[-1]['data_offset'] = self.offsets[-1]

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

        file_length = channel_filename.stat().st_size
        self.segments[-1]['length'] = int((file_length - self.offsets[-1]) / BLK_SIZE * BLK_LENGTH)

        for seg in self.segments:
            seg['end'] = seg['start'] + seg['length']

        self.gain = array(gain)
        n_samples = self.segments[-1]['end']

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
        data_length = endsam - begsam
        dat = empty((len(chan), data_length))
        dat.fill(NaN)

        blocks_dat, blocks_disk = _prepare_blocks(self.segments)

        all_blocks = _select_blocks(blocks_dat, begsam, endsam)
        for i_chan, sel_chan in enumerate(chan):
            with self.channels[sel_chan].open('rb') as f:
                for i_block in all_blocks:
                    i_dat = blocks_dat[i_block, :] - begsam
                    i_disk = blocks_disk[i_block, :]

                    f.seek(i_disk[0])
                    # read whole block
                    x = array(unpack(DAT_FMT, f.read(i_disk[1] - i_disk[0])))
                    beg_dat = max(i_dat[0], 0)
                    end_dat = min(i_dat[1], data_length)
                    beg_x = max(0, - i_dat[0])
                    segment_length = min(i_dat[1], data_length) - i_dat[0]
                    end_x = min(len(x), segment_length)
                    dat[i_chan, beg_dat:end_dat] = x[beg_x:end_x]

        return dat * self.gain[chan, None]

    def return_markers(self):
        """Read the markers from the .events file

        """
        all_markers = (
            self.messages
            + _segments_to_markers(self.segments)
            + _read_all_channels_events(self.events_file, 0, self.s_freq)
            )
        return sorted(all_markers, key=lambda x: x['start'])


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

    TODO
    ----
    Check that all the recordings have the same channels and frequency
    """
    root = ElementTree.parse(openephys_file).getroot()

    recordings = []
    for recording in root:
        recordings.append({
            's_freq': float(recording.attrib['samplerate']),
            'number': int(recording.attrib['number']),
            'channels': [],
        })
        channels = []
        for processor in recording:
            for channel in processor:
                channels.append(channel.attrib)
        recordings[-1]['channels'] = channels

    return recordings


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
    locale.setlocale(locale.LC_TIME, 'en_US.utf-8')

    root = ElementTree.parse(settings_file).getroot()
    for e0 in root:
        if e0.tag == 'INFO':
            for e1 in e0:
                if e1.tag == 'DATE':
                    break

    return datetime.strptime(e1.text, '%d %b %Y %H:%M:%S')


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


def _segments_to_markers(segments):
    mrk = []
    for i, seg in enumerate(segments):
        mrk.append({
            'name': f'START RECORDING #{i}',
            'chan': None,
            'start': seg['start'] / seg['s_freq'],
            'end': seg['start'] / seg['s_freq'],
        })
        mrk.append({
            'name': f'END RECORDING #{i}',
            'chan': None,
            'start': seg['end'] / seg['s_freq'],
            'end': seg['end'] / seg['s_freq'],
        })

    return mrk

def _read_messages_events(messages_file):
    messages = []
    segments = []
    header = True

    with messages_file.open() as f:
        for l in f:

            m_time = search(r'\d+ Software time: \d+@\d+Hz', l)
            m_start = search(r'start time: (\d+)@(\d+)Hz', l)
            m_event = match(r'(\d+) (.+)', l)

            if m_time:
                continue   # ignore Software time

            elif m_start:
                if header:
                    offset = int(m_start.group(1))
                    s_freq = int(m_start.group(2))
                    header = False

                segments.append({
                    'start': int(m_start.group(1)) - offset,
                    's_freq': int(m_start.group(2)),
                    })

            elif m_event:
                time = int(m_event.group(1))
                messages.append({
                    'name': m_event.group(2),
                    'start': (time - offset) / s_freq,
                    'end': (time - offset) / s_freq,
                    'chan': None,
                })

    return segments, messages


def _read_all_channels_events(events_file, offset, s_freq):

    file_read = [
        ('timestamps', '<i8'),
        ('sampleNum', '<i2'),
        ('eventType', '<u1'),
        ('nodeId', '<u1'),
        ('eventId', '<u1'),
        ('channel', '<u1'),
        ('recordingNumber', '<u2'),
        ]

    with events_file.open('rb') as f:
        f.seek(HDR_LENGTH)
        evt = fromfile(f, file_read)

    mrk = []
    for evt_type in unique(evt['eventType']):
        timestamps = evt[evt['eventType'] == evt_type]['timestamps']
        onsets = timestamps[::2]
        offsets = timestamps[1::2]

        for i_on, i_off in zip(onsets, offsets):
            mrk.append({
                'name': str(evt_type),
                'start': (i_on - offset) / s_freq,
                'end': (i_off - offset) / s_freq,
                'chan': None,
            })

    return mrk


def _prepare_blocks(segments):

    blocks_dat = []
    blocks_disk = []

    for seg in segments:
        n_blocks = ceil(seg['length'] / BLK_LENGTH)
        for i_blk in range(n_blocks):
            blocks_dat.append([
                i_blk * BLK_LENGTH + seg['start'],
                i_blk * BLK_LENGTH + BLK_LENGTH + seg['start'],
            ])
            blocks_disk.append([
                seg['data_offset'] + BEG_BLK_SIZE + i_blk * DAT_FMT_SIZE,
                seg['data_offset'] + BEG_BLK_SIZE + i_blk * DAT_FMT_SIZE + DAT_FMT_SIZE,
            ])

    blocks_dat = array(blocks_dat)
    blocks_disk = array(blocks_disk)

    blocks_disk

    return blocks_dat, blocks_disk


def _select_blocks(blocks_dat, begsam, endsam):
    all_blocks = ((blocks_dat[:, 1] - begsam) > 0) & ((endsam - blocks_dat[:, 0]) > 0)
    return where(all_blocks)[0]
