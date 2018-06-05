from datetime import datetime
from logging import getLogger
from os import SEEK_CUR
from pathlib import Path
from struct import unpack
from xml.etree.ElementTree import parse

from numpy import (append, asarray, cumsum, diff, empty, NaN, sum,
                   where, ndarray, unique)

from .utils import DEFAULT_DATETIME


lg = getLogger(__name__)


class EgiMff:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    """
    def __init__(self, filename):
        self.filename = Path(filename)
        self._signal = []
        self._block_hdr = []
        self._i_data = []
        self._nchan_signal1 = []  # n of channels in signal1
        self._n_samples = []
        self._orig = {}

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
            additional information taken directly from the header

        """
        orig = {}
        for xml_file in self.filename.glob('*.xml'):
            if xml_file.stem[0] != '.':
                orig[xml_file.stem] = parse_xml(str(xml_file))

        signals = sorted(self.filename.glob('signal*.bin'))

        for signal in signals:
            block_hdr, i_data = read_all_block_hdr(signal)
            self._signal.append(signal)
            self._block_hdr.append(block_hdr)
            self._i_data.append(i_data)
            n_samples = asarray([x['n_samples'][0] for x in block_hdr], 'q')
            self._n_samples.append(n_samples)

        try:
            subj_id = orig['subject'][0][0]['name']
        except KeyError:
            subj_id = ''
        try:
            start_time = datetime.strptime(orig['info'][0]['recordTime'][:26],
                                           '%Y-%m-%dT%H:%M:%S.%f')
        except KeyError:
            start_time = DEFAULT_DATETIME
        self.start_time = start_time

        videos = (list(self.filename.glob('*.mp4')) +  # as described in specs
                  list(self.filename.glob('*.mov')))  # actual example
        videos = [x for x in videos if x.stem[0] != '.']  # remove hidden files

        if len(videos) > 1:
            lg.warning('More than one video present: ' + ', '.join(videos))
        self._videos = videos

        # it only works if they have all the same sampling frequency
        s_freq = [x[0]['freq'][0] for x in self._block_hdr]
        assert all([x == s_freq[0] for x in s_freq])
        SIGNAL = 0
        s_freq = self._block_hdr[SIGNAL][0]['freq'][0]
        n_samples = sum(self._n_samples[SIGNAL])

        chan_name, self._nchan_signal1 = _read_chan_name(orig)
        self._orig = orig

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

    def return_dat(self, chan, begsam, endsam):
        """Return the data as 2D numpy.ndarray.

        Parameters
        ----------
        chan : list
            indices of the channels to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A 2d matrix, with dimension chan X samples

        Notes
        -----
        This format is tricky for both channels and samples. For the samples,
        we just use the boundaries in the block header. For the channels, we
        assume that there are max two signals, one EEG and one PIB box. We
        just use the boundary between them to define if a channel belongs to
        the first group or to the second.

        TODO
        ----
        use wonambi.ioeeg.utils._select_blocks here, but you need to test it
        with a PIB box.
        """
        assert begsam < endsam

        data = empty((len(chan), endsam - begsam))
        data.fill(NaN)

        chan = asarray(chan)

        # we assume there are only two signals
        signals_to_read = []
        if (chan < self._nchan_signal1).any():
            signals_to_read.append(0)
        if (chan >= self._nchan_signal1).any():
            signals_to_read.append(1)

        for one_signal in signals_to_read:
            if one_signal == 0:
                i_chan_data = chan < self._nchan_signal1
                i_chan_rec = chan[i_chan_data]

            if one_signal == 1:
                i_chan_data = chan >= self._nchan_signal1
                i_chan_rec = chan[i_chan_data] - self._nchan_signal1

            x = self._n_samples[one_signal]
            x1 = cumsum(append(0, x))

            # begrec is -1 when begsam is before start of the recordings
            begrec = where(begsam < x1)[0][0] - 1
            try:
                endrec = where(endsam < x1)[0][0] - 1
            except IndexError:
                endrec = len(x)

            f = self._signal[one_signal].open('rb')

            i0 = 0
            for rec in range(begrec, endrec + 1):

                # if begsam is before start of the recordings, we just shift the baseline
                if rec == -1:
                    i0 = - begsam
                    continue

                # if endsam is after end of the recordings, we just stop here
                if rec == len(self._n_samples[one_signal]):
                    break

                if rec == begrec:
                    begpos_rec = begsam - x1[rec]
                else:
                    begpos_rec = 0

                if rec == endrec:
                    endpos_rec = endsam - x1[rec]
                else:
                    endpos_rec = x[rec]

                i1 = i0 + endpos_rec - begpos_rec

                lg.debug('data {: 8d}-{: 8d}, rec ({}) {: 5d} - {: 5d}'.format(i0, i1, rec, begpos_rec, endpos_rec))

                rec_dat = _read_block(f,
                                      self._block_hdr[one_signal][rec],
                                      self._i_data[one_signal][rec])

                data[i_chan_data, i0:i1] = rec_dat[i_chan_rec,
                                                   begpos_rec:endpos_rec]
                i0 = i1

            f.close()

        return data

    def return_markers(self):
        """"""
        xml_files = self._orig.keys()
        xml_events = [x for x in xml_files if x[:7] == 'Events_']

        markers = []
        for xml in xml_events:
            for event in self._orig[xml][2:]:
                event_start = datetime.strptime(event['beginTime'][:26],
                                                '%Y-%m-%dT%H:%M:%S.%f')
                start = (event_start - self.start_time).total_seconds()

                marker = {'name': event['code'],
                          'start': start,
                          'end': start + float(event['duration']) / 1e9,
                          'chan': None,
                          }
                markers.append(marker)

        return markers

    def return_videos(self, begtime, endtime):
        """It returns the videos and beginning and end time of the video
        segment. The MFF video format is not well documented. As far as I can
        see, the manual 20150805 says that there might be multiple .mp4 files
        but I only see one .mov file (and no way to specify which video file to
        read). In addition, there is a file "po_videoSyncups.xml" which seems
        to contain some time information, but the sampleTime does not start at
        zero, but at a large number. I don't know how to use the info in
        po_videoSyncups.xml.

        Parameters
        ----------
        begtime : float
            start time of the period of interest
        endtime : float
            end time of the period of interest

        Returns
        -------
        list of one path
            list with only one element
        float
            start time of the video
        float
            end time of the video
        """
        try:
            self._orig['po_videoSyncups']
        except KeyError:
            raise OSError('No po_videoSyncups.xml in folder to sync videos')

        if not self._videos:
            raise OSError('No mp4 video files')

        mp4_file = self._videos[:1]  # make clear we only use the first video

        return mp4_file, begtime, endtime


def _read_block(filename, block_hdr, i):
    f = filename

    # Can we assume constant depth across blocks?
    depth = unique(block_hdr['depth'])
    assert(len(depth) == 1)
    n_bytes = (depth[0] / 8).astype('B')

    if n_bytes == 2:
        data_type = '<h'
    elif n_bytes == 4:
        data_type = '<f'
    elif n_bytes == 8:
        data_type = '<d'
    else:
        raise ValueError("Invalid depth parameter.")

    f.seek(i)

    return ndarray((block_hdr['n_signals'], block_hdr['n_samples'][0]),
                   data_type,
                   f.read(sum(n_bytes * block_hdr['n_samples'])))


def read_block_hdr(f):

    version = unpack('<I', f.read(4))[0]
    hdr_size = unpack('<I', f.read(4))[0]
    data_size = unpack('<I', f.read(4))[0]
    n_signals = unpack('<I', f.read(4))[0]

    offset = asarray(unpack('<' + 'I' * n_signals, f.read(4 * n_signals)), 'I')

    depth = empty(n_signals, 'B')
    freq = empty(n_signals, 'I')
    for j in range(n_signals):
        depth[j] = unpack('<B', f.read(1))[0]
        freq[j] = unpack('<I', f.read(3) + b'\x00')[0]

    n_samples = diff(offset)
    n_samples = append(n_samples, data_size - offset[-1])
    n_samples = (n_samples / (depth / 8)).astype('I')

    opt_hdr_size = unpack('<I', f.read(4))[0]
    if opt_hdr_size > 0:
        opt_hdr_type = unpack('<I', f.read(4))[0]
        n_blocks = unpack('<Q', f.read(8))[0]
        n_smp = unpack('<Q', f.read(8))[0]  # unreliable
        n_signals_opt = unpack('<I', f.read(4))[0]
    else:
        n_blocks = None
        n_smp = None
        n_signals_opt = None

    opt_hdr = {'n_blocks': n_blocks,
               'n_smp': n_smp,
               'n_signals_opt': n_signals_opt}

    hdr = {'version': version,
           'hdr_size': hdr_size,
           'data_size': data_size,
           'n_signals': n_signals,
           'offset': offset,
           'depth': depth,
           'freq': freq,
           'n_samples': n_samples,
           'opt_hdr_size': opt_hdr_size,
           'opt_hdr': opt_hdr,
           }

    return hdr


def read_all_block_hdr(filename):

    with filename.open('rb') as f:

        block_hdr = []
        i_data = []

        while True:
            version_bytes = f.read(4)
            if not version_bytes:
                break
            version = unpack('<I', version_bytes)[0]

            if version:
                f.seek(-4, SEEK_CUR)  # re-read version
                block_hdr.append(read_block_hdr(f))

            else:
                block_hdr.append(block_hdr[-1])

            i_data.append(f.tell())
            f.seek(block_hdr[-1]['data_size'], SEEK_CUR)

        i_data = asarray(i_data, 'q')

    return block_hdr, i_data


def parse_xml(xml_file):
    xml = parse(xml_file)
    root = xml.getroot()
    return xml2list(root)


def ns(s):
    """remove namespace, but only it there is a namespace to begin with"""
    if '}' in s:
        return '}'.join(s.split('}')[1:])
    else:
        return s


def xml2list(root):
    output = []

    for element in root:

        if element:

            if element[0].tag != element[-1].tag:
                output.append(xml2dict(element))
            else:
                output.append(xml2list(element))

        elif element.text:
            text = element.text.strip()
            if text:
                tag = ns(element.tag)
                output.append({tag: text})

    return output


def xml2dict(root):
    """Use functions instead of Class and remove namespace based on:
    http://stackoverflow.com/questions/2148119
    """
    output = {}
    if root.items():
        output.update(dict(root.items()))

    for element in root:
        if element:
            if len(element) == 1 or element[0].tag != element[1].tag:
                one_dict = xml2dict(element)
            else:
                one_dict = {ns(element[0].tag): xml2list(element)}

            if element.items():
                one_dict.update(dict(element.items()))
            output.update({ns(element.tag): one_dict})

        elif element.items():
            output.update({ns(element.tag): dict(element.items())})

        else:
            output.update({ns(element.tag): element.text})

    return output


def _read_chan_name(orig):
    """Read channel labels, which can be across xml files.

    Parameters
    ----------
    orig : dict
        contains the converted xml information

    Returns
    -------
    list of str
        list of channel names
    ndarray
        vector to indicate to which signal a channel belongs to

    Notes
    -----
    This assumes that the PIB Box is the second signal.
    """
    sensors = orig['sensorLayout'][1]

    eeg_chan = []
    for one_sensor in sensors:
        if one_sensor['type'] in ('0', '1'):
            if one_sensor['name'] is not None:
                eeg_chan.append(one_sensor['name'])
            else:
                eeg_chan.append(one_sensor['number'])

    pns_chan = []
    if 'pnsSet' in orig:
        pnsSet = orig['pnsSet'][1]
        for one_sensor in pnsSet:
            pns_chan.append(one_sensor['name'])

    return eeg_chan + pns_chan, len(eeg_chan)
