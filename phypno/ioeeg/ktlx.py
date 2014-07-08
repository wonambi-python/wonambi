"""Module reads and writes header and data for KTLX data. The files are:
  - .eeg (patient information)
  - .ent (notes, sometimes with a backup file called .ent.old)
  - .erd (raw data)
  - .etc (table of content)
  - .snc (synchronization file)
  - .stc (segmented table of content)
  - .vtc (video table of content)
  - .avi (videos)

There is only one of these files in the directory, except for .erd, .etc., .avi
These files are numbered in the format _%03d, except for the first one, which
is not _000 but there is no extension, for backwards compatibility.

This module contains functions to read each of the files, the files are called
_read_EXT where EXT is one of the extensions.

"""
from logging import getLogger
lg = getLogger(__name__)

from binascii import hexlify
from datetime import timedelta, datetime
from glob import glob
from math import ceil
from os import SEEK_END
from os.path import basename, join, exists, splitext
from re import sub
from struct import unpack
from tempfile import tempdir
from numpy import (NaN, ones, concatenate, expand_dims, where, asarray, empty,
                   memmap, int32)

BITS_IN_BYTE = 8
# http://support.microsoft.com/kb/167296
# How To Convert a UNIX time_t to a Win32 FILETIME or SYSTEMTIME
EPOCH_AS_FILETIME = 116444736000000000  # January 1, 1970 as MS file time
HUNDREDS_OF_NANOSECONDS = 10000000

ZERO = timedelta(0)
HOUR = timedelta(hours=1)
from os.path import expanduser
home = expanduser('~')
temp_dir = join(tempdir, 'phypno_cache')
lg.info('Temporary Directory with data: ' + temp_dir)


def get_erd(sample, all_beg, all_end):
    """Get the ERD for one specific sample.

    Parameters
    ----------
    sample : int
        sample of interest
    all_beg : ndarray
        vector of the first sampling points
    all_end : ndarray
        vector of the last sampling points

    Returns
    -------
    int or None
        index of the ERD containing the sample (or None if not found)

    """
    try:
        return where((all_beg <= sample) & (sample <= all_end))[0][0]
    except IndexError:
        return None


def get_date_idx(time_of_interest, start_time, end_time):
    idx = None
    for i in range(len(start_time)):
        if time_of_interest >= start_time[i] and time_of_interest <= end_time[i]:
            idx = i
            break

    return idx


def convert_sample_to_video_time(sample, orig_s_freq, sampleStamp,
                                 sampleTime):
    """Convert sample number to video time, using snc information.

    Parameters
    ----------
    sample : int
        sample that you want to convert in time
    orig_s_freq : int
        sampling frequency (used as backup)
    sampleStamp : list of int
        Sample number from start of study
    sampleTime : list of datetime.datetime
        File time representation of sampleStamp

    Returns
    -------
    instance of datetime
        absolute time of the sample.

    Notes
    -----
    Note that there is a discrepancy of 4 or 5 hours between the time in
    snc and the time in the header. I'm pretty sure that the time in the
    header is accurate, so we use that. I think that the time in snc does
    not take into account the time zone (that'd explain the 4 or 5
    depending on summertime). This time is only used to get the right video
    so we call this "video time".

    """
    if sample < sampleStamp[0]:
        s_freq = orig_s_freq
        id0 = 0
    elif sample > sampleStamp[-1]:
        s_freq = orig_s_freq
        id0 = len(sampleStamp) - 1
    else:
        id0 = where(asarray(sampleStamp) <= sample)[0][-1]
        id1 = where(asarray(sampleStamp) >= sample)[0][0]

        if id0 == id1:
            return sampleTime[id0]
        s_freq = ((sampleStamp[id1] - sampleStamp[id0]) /
                  (sampleTime[id1] - sampleTime[id0]).total_seconds())
    time_diff = timedelta(seconds=(sample - sampleStamp[id0]) / s_freq)
    return sampleTime[id0] + time_diff


def _calculate_conversion(hdr):
    """Calculate the conversion factor.

    Returns
    -------
    conv_factor : numpy.ndarray
        channel-long vector with the channel-specific conversion factor

    Notes
    -----
    Final units are microvolts

    """
    discardbits = hdr['discardbits']
    n_chan = hdr['num_channels']

    if hdr['headbox_type'][0] in (1, 3):
        # all channels
        factor = ones((n_chan)) * (8711. / (2 ** 21 - 0.5)) * 2 ** discardbits

    elif hdr['headbox_type'][0] == 4:
        # 0 - 23
        ch1 = ones((24)) * (8711. / (2 ** 21 - 0.5)) * 2 ** discardbits
        # 24 - 27
        ch2 = ones((4)) * ((5000000. / (2 ** 10 - 0.5)) / (2 ** 6)) * 2 ** discardbits

        factor = concatenate((ch1, ch2))

    elif hdr['headbox_type'][0] == 9:
        # 0 - 32
        ch1 = ones((33)) * (8711. / ((2 ** 21) - 0.5)) * 2 ** discardbits
        # 33 - 34
        ch2 = ones((2)) * (1 / (2 ** 6)) * 2 ** discardbits

        factor = concatenate((ch1, ch2))

    elif hdr['headbox_type'][0] == 21:
        # 0 -127
        ch1 = ones((128)) * (8711. / ((2 ** 21) - 0.5)) * 2 ** discardbits
        # 128 - 129
        ch2 = ones((2)) * (1 / (2 ** 6)) * 2 ** discardbits
        # 130 - 255
        ch3 = ones((126)) * (8711. / ((2 ** 21) - 0.5)) * 2 ** discardbits

        factor = concatenate((ch1, ch2, ch3))

    elif hdr['headbox_type'][0] == 22:
        # 0 -31
        ch1 = ones((32)) * (8711. / ((2 ** 21) - 0.5)) * 2 ** discardbits
        # 32 - 39
        ch2 = ones((8)) * ((10800000. / 65536.) / (2 ** 6)) * 2 ** discardbits
        # 40 - 41
        ch3 = ones((2)) * (1 / (2 ** 6)) * 2 ** discardbits
        # 42
        ch4 = ones((1)) * ((10800000. / 65536.) / (2 ** 6)) * 2 ** discardbits

        factor = concatenate((ch1, ch2, ch3, ch4))

    else:
        raise NotImplementedError('Implement conversion factor for headbox ' +
                                  str(hdr['headbox_type'][0]))

    return factor[:n_chan]


def _filetime_to_dt(ft):
    """Converts a Microsoft filetime number to a Python datetime. The new
    datetime object is time zone-naive but is equivalent to tzinfo=utc.

    """
    # Get seconds and remainder in terms of Unix epoch
    s, ns100 = divmod(ft - EPOCH_AS_FILETIME, HUNDREDS_OF_NANOSECONDS)
    # Convert to datetime object
    dt = datetime.utcfromtimestamp(s)
    # Add remainder in as microseconds. Python 3.2 requires an integer
    dt = dt.replace(microsecond=(ns100 // 10))
    return dt


def _find_channels(note):
    """Find the channel names within a string.

    The channel names are stored in the .ent file. We can read the file with
    _read_ent and we can parse most of the notes (comments) with _read_notes
    however the note containing the montage cannot be read because it's too
    complex. So, instead of parsing it, we just pass the string of the note
    around. This function takes the string and finds where the channel
    definition is.

    Parameters
    ----------
    note : str
        string read from .ent file, it's the note which contains montage.

    Returns
    -------
    chan_name : list of str
        the names of the channels.

    """
    id_ch = note.index('ChanNames')
    chan_beg = note.index('(', id_ch)
    chan_end = note.index(')', chan_beg)
    note_with_chan = note[chan_beg + 1:chan_end]
    return [x.strip('" ') for x in note_with_chan.split(',')]


def _make_str(t_in):
    t_out = []
    for t in t_in:
        if t == b'\x00':
            break
        t_out.append(t.decode('utf-8'))
    return ''.join(t_out)


def _read_eeg(eeg_file):
    """Reads eeg file, but it doesn't work, the data is in text format, but
    based on Excel. You can read it from the editor, there are still a couple
    of signs that are not in Unicode.

    TODO: parse the text of EEG, if it's interesting

    Notes
    -----
    The patient information file consists of a single null terminated string
    following the generic file header. The string encodes all the patient
    information in a list format defined by a hierarchy of name value pairs.

    """
    pass


def _read_ent(ent_file):
    """Read notes stored in .ent file.

    This is a basic implementation, that relies on turning the information in
    the string in the dict format, and then evaluate it. It's not very flexible
    and it might not read some notes, but it's fast. I could not implement a
    nice, recursive approach.

    Returns
    -------
    allnote : a list of dict
        where each dict contains keys such as:
          - type
          - length : length of the note in B,
          - prev_length : length of the previous note in B,
          - unused,
          - value : the actual content of the note.

    Notes
    -----
    The notes are stored in a format called 'Excel list' but could not find
    more information. It's based on "(" and "(.", and I found it very hard to
    parse. With some basic regex and substitution, it can be evaluated into
    a dict, with sub dictionaries. However, the note containing the name of the
    electrodes (I think they called it "montage") cannot be parsed, because
    it's too complicated. If it cannot be converted into a dict, the whole
    string is passed as value.

    """
    with open(ent_file, 'rb') as f:
        f.seek(352)  # end of header

        note_hdr_length = 16

        allnote = []
        while True:
            note = {}
            note['type'], = unpack('<i', f.read(4))
            note['length'], = unpack('<i', f.read(4))
            note['prev_length'], = unpack('<i', f.read(4))
            note['unused'], = unpack('<i', f.read(4))
            if not note['type']:
                break
            s = f.read(note['length'] - note_hdr_length)
            s = s[:-2]  # it ends with one empty byte
            s = s.decode('utf-8')
            s1 = s.replace('\n', ' ')
            s1 = s1.replace('\\xd ', '')
            s1 = s1.replace('(.', '{')
            s1 = sub(r'\(([A-Za-z0-9," ]*)\)', r'[\1]', s1)
            s1 = s1.replace(')', '}')
            # s1 = s1.replace('",', '" :')
            s1 = sub(r'(\{[\w"]*),', r'\1 :', s1)
            s1 = s1.replace('{"', '"')
            s1 = s1.replace('},', ',')
            s1 = s1.replace('}}', '}')
            s1 = sub(r'\(([0-9 ,-\.]*)\}', r'[\1]', s1)
            try:
                note['value'] = eval(s1)
            except:
                note['value'] = s
            allnote.append(note)
    return allnote


def _read_erd(erd_file, n_samples):
    """Read the raw data and return a matrix, converted to microvolts.

    Parameters
    ----------
    erd_file : str
        one of the .erd files to read
    n_samples : int
        the number of samples to read, based on .stc

    Returns
    -------
    data : numpy.ndarray
        2d matrix with the data, as read from the file

    Error
    -----
    It checks whether the event byte (the first byte) is x00 as expected.
    It can also be x01, meaning that an event was generated by an external
    trigger. According to the manual, "a photic stimulator is the only
    supported device which generates an external trigger."
    If the eventbyte is something else, it throws an error.

    Notes
    -----
    Each sample point consists of these parts:
      - Event Byte
      - Frequency byte (only if file_schema >= 8 and one chan has != freq)
      - Delta mask (only if file_schema >= 8)
      - Delta Information
      - Absolute Channel Values

    Event Byte:
      Bit 0 of the event byte indicates the presence of the external trigger
      during the sample period. It's very rare.

    Delta Mask:
      Bit-mask of a size int( number_of_channels / 8 + 0.5). Each 1 in the mask
      indicates that corresponding channel has 2*n bit delta, 0 means that
      corresponding channel has n bit delta.
      The rest of the byte of the delta mask is filled with "1".
      If file_schema <= 7, it generates a "fake" delta, where everything is 0.

    Some channels are shorted (i.e. not recorded), however they are stored in
    a non-intuitive way: deltamask takes them into account, but for the rest
    they are never used/recorded. So, we need to keep track both of all the
    channels (including the non-shorted) and of the actual channels only.

    When we save the data as memory-mapped, we only save the real channels.
    However, the data in the output have both shorted and non-shorted channels.
    Shorted channels have NaN's only.

    """
    hdr = _read_hdr_file(erd_file)
    n_allchan = hdr['num_channels']
    shorted = hdr['shorted']  # does this exist for Schema 7 at all?
    n_shorted = sum(shorted)
    n_chan = n_allchan - n_shorted
    safe_name = "".join([x if x.isalnum() else "_" for x in basename(erd_file)])
    memmap_file = join(temp_dir, safe_name)
    if exists(memmap_file):
        lg.info('Reading existing file: ' + memmap_file)
        dat = memmap(memmap_file, mode='c', shape=(n_chan, n_samples),
                     dtype=int32)
    else:
        lg.info('Writing new file: ' + memmap_file)
        dat = memmap(memmap_file, mode='w+', shape=(n_chan, n_samples),
                     dtype=int32)

        # deltamask length (use all channels)
        l_deltamask = int(ceil(n_allchan / BITS_IN_BYTE))
        with open(erd_file, 'rb') as f:
            filebytes = f.read()

        if hdr['file_schema'] in (7,):
            i = 4560
            abs_delta = b'\x80'  # one byte: 10000000

        if hdr['file_schema'] in (8, 9):
            i = 8656
            abs_delta = b'\xff\xff'

        for sam in range(n_samples):

            # Event Byte
            eventbite = filebytes[i:i + 1]
            i += 1
            if eventbite == b'':
                break
            try:
                assert eventbite in (b'\x00', b'\x01')
            except:
                raise Exception('at pos ' + str(i) +
                                ', eventbite (should be x00 or x01): ' +
                                str(eventbite))

            # Delta Information
            if hdr['file_schema'] in (7,):
                deltamask = '0' * n_chan

            if hdr['file_schema'] in (8, 9):
                # read single bits as they appear, one by one
                byte_deltamask = unpack('<' + 'B' * l_deltamask,
                                        filebytes[i:i + l_deltamask])
                i += l_deltamask
                deltamask = ['{0:08b}'.format(x)[::-1] for x in byte_deltamask]
                deltamask = ''.join(deltamask)

            i_chan = 0  # excluding the shorted channels
            read_absvalue = [False] * n_chan

            for i_allchan, m in enumerate(deltamask[:n_allchan]):

                if shorted[i_allchan]:
                    continue

                if m == '1':
                    val = filebytes[i:i + 2]
                    i += 2
                elif m == '0':
                    val = filebytes[i:i + 1]
                    i += 1

                if val == abs_delta:
                    read_absvalue[i_chan] = True
                else:
                    if m == '1':
                        dat[i_chan, sam] = (dat[i_chan, sam - 1] +
                                            unpack('<h', val)[0])
                    elif m == '0':
                        dat[i_chan, sam] = (dat[i_chan, sam - 1] +
                                            unpack('<b', val)[0])

                i_chan += 1

            for i_chan, to_read in enumerate(read_absvalue):
                if to_read:
                    dat[i_chan, sam] = unpack('<i', filebytes[i:i + 4])[0]
                    i += 4

    # fill up the output data, put NaN for shorted channels
    if n_shorted > 0:
        full_channels = where(asarray([x == 0 for x in shorted]))[0]
        output = empty((n_allchan, n_samples))
        output.fill(NaN)
        output[full_channels, :] = dat
    else:
        output = dat

    factor = _calculate_conversion(hdr)
    return expand_dims(factor, 1) * output


def _read_etc(etc_file):
    """Return information about etc.

    ETC contains only 4 4-bytes, I cannot make sense of it. The EEG file format
    does not have an explanation for ETC, it says it's similar to the end of
    STC, which has 4 int, but the values don't match.

    """
    with open(etc_file, 'rb') as f:
        f.seek(352)  # end of header
        v1 = unpack('<i', f.read(4))[0]
        v2 = unpack('<i', f.read(4))[0]
        v3 = unpack('<i', f.read(4))[0]  # always zero?
        v4_a = unpack('<h', f.read(2))[0]  # they look like two values
        v4_b = unpack('<h', f.read(2))[0]  # maybe this one is unsigned (H)

        f.seek(352)  # end of header
        # lg.debug(hexlify(f.read(16)))
    return v1, v2, v3, (v4_a, v4_b)


def _read_snc(snc_file):
    """Read Synchronization File and return sample stamp and time

    Returns
    -------
    sampleStamp : list of int
        Sample number from start of study
    sampleTime : list of datetime.datetime
        File time representation of sampleStamp

    Notes
    -----
    The synchronization file is used to calculate a FILETIME given a sample
    stamp (and vise-versa). Theoretically, it is possible to calculate a sample
    stamp's FILETIME given the FILETIME of sample stamp zero (when sampling
    started) and the sample rate. However, because the sample rate cannot be
    represented with full precision the accuracy of the FILETIME calculation is
    affected.

    To compensate for the lack of accuracy, the synchronization file maintains
    a sample stamp-to-computer time (called, MasterTime) mapping. Interpolation
    is then used to calculate a FILETIME given a sample stamp (and vise-versa).

    The attributes, sampleStamp and sampleTime, are used to predict (using
    interpolation) the FILETIME based upon a given sample stamp (and
    vise-versa). Currently, the only use for this conversion process is to
    enable correlation of EEG (sample_stamp) data with other sources of data
    such as Video (which works in FILETIME).

    """
    with open(snc_file, 'rb') as f:
        filebytes = f.read()
    i = 352  # end of header

    sampleStamp = []
    sampleTime = []
    while i < len(filebytes):
        sampleStamp.append(unpack('<i', filebytes[i:(i + 4)])[0])
        i += 4
        sampleTime.append(_filetime_to_dt(unpack('<q',
                                                 filebytes[i:(i + 8)])[0]))
        i += 8

    return sampleStamp, sampleTime


def _read_stc(stc_file):
    """Read Segment Table of Contents file.

    Returns
    -------
    hdr : dict
        - next_segment : Sample frequency in Hertz
        - final : Number of channels stored
        - padding : Padding

    all_stamp : list of dict
        - segment_name : Name of ERD / ETC file segment
        - start_stamp : First sample stamp that is found in the ERD / ETC pair
        - end_stamp : Last sample stamp that is still found in the ERD / ETC
        pair
        - sample_num : Number of samples recorded to the point that corresponds
        to start_stamp. This number accumulates over ERD / ETC pairs and is
        equal to sample_num of the first entry in the ETC file referenced by
        this STC entry


    Notes
    -----
    The Segment Table of Contents file is an index into pairs of (raw data file
    / table of contents file). It is used for mapping samples file segments.
    EEG raw data is split into segments in order to break a single file size
    limit (used to be 2GB) while still allowing quick searches. This file ends
    in the extension '.stc'. Default segment size (size of ERD file after which
    it is closed and new [ERD / ETC] pair is opened) is 50MB. The file starts
    with a generic EEG file header, and is followed by a series of fixed length
    records called the STC entries. ERD segments are named according to the
    following schema:
      - <FIRST_NAME>, <LAST_NAME>_<GUID>.ERD (first)
      - <FIRST_NAME>, <LAST_NAME>_<GUID>.ETC (first)
      - <FIRST_NAME>, <LAST_NAME>_<GUID>_<INDEX>.ERD (second and subsequent)
      - <FIRST_NAME>, <LAST_NAME>_<GUID>_<INDEX>.ETC (second and subsequent)

    <INDEX> is formatted with "%03d" format specifier and starts at 1 (initial
    value being 0 and omitted for compatibility with the previous versions).

    """
    with open(stc_file, 'rb') as f:
        f.seek(0, SEEK_END)
        endfile = f.tell()
        f.seek(352)  # end of header
        hdr = {}
        hdr['next_segment'] = unpack('<i', f.read(4))[0]
        hdr['final'] = unpack('<i', f.read(4))[0]
        hdr['padding'] = unpack('<' + 'i' * 12, f.read(48))

        all_stamp = []

        while True:
            if f.tell() == endfile:
                break
            stamp = {}
            stamp['segment_name'] = _make_str(unpack('c' * 256, f.read(256)))
            stamp['start_stamp'] = unpack('<i', f.read(4))[0]
            stamp['end_stamp'] = unpack('<i', f.read(4))[0]
            stamp['sample_num'] = unpack('<i', f.read(4))[0]
            stamp['sample_span'] = unpack('<i', f.read(4))[0]

            all_stamp.append(stamp)

    return hdr, all_stamp


def _read_vtc(vtc_file):
    """Read the VTC file.

    Parameters
    ----------
    vtc_file : str
        path to vtc file

    Returns
    -------
    mpg_file : list of str
        list of avi files
    start_time : list of datetime
        list of start time of the avi files
    end_time : list of datetime
        list of end time of the avi files

    """
    with open(vtc_file, 'rb') as f:
        filebytes = f.read()

    hdr = {}
    hdr['file_guid'] = hexlify(filebytes[:16])
    # not sure about the 4 Bytes inbetween

    i = 20
    mpg_file = []
    start_time = []
    end_time = []
    while i < len(filebytes):
        mpg_file.append(_make_str(unpack('c' * 261, filebytes[i:i + 261])))
        i += 261
        Location = filebytes[i:i + 16]
        correct = b'\xff\xfe\xf8^\xfc\xdc\xe5D\x8f\xae\x19\xf5\xd6"\xb6\xd4'
        assert Location == correct
        i += 16
        start_time.append(_filetime_to_dt(unpack('<q',
                                                 filebytes[i:(i + 8)])[0]))
        i += 8
        end_time.append(_filetime_to_dt(unpack('<q',
                                               filebytes[i:(i + 8)])[0]))
        i += 8

    return mpg_file, start_time, end_time


def _read_hdr_file(ktlx_file):
    """Reads header of one KTLX file.

    Parameters
    ----------
    ktlx_file : str
        name of one of the ktlx files inside the directory (absolute path)

    Returns
    -------
    dict
        dict with information about the file

    Notes
    -----
    p.3: says long, but python-long requires 8 bytes, so we use f.read(4)

    GUID is correct, BUT little/big endian problems somewhere

    """
    with open(ktlx_file, 'rb') as f:

        hdr = {}
        assert f.tell() == 0

        hdr['file_guid'] = hexlify(f.read(16))
        hdr['file_schema'], = unpack('<H', f.read(2))
        if not hdr['file_schema'] in (1, 3, 7, 8, 9):
            raise NotImplementedError('Reading header not implemented for ' +
                                      'file_schema ' + str(hdr['file_schema']))

        hdr['base_schema'], = unpack('<H', f.read(2))
        if not hdr['base_schema'] == 1:  # p.3: base_schema 0 is rare, I think
            raise NotImplementedError('Reading header not implemented for ' +
                                      'base_schema ' + str(hdr['base_schema']))

        hdr['creation_time'] = datetime.fromtimestamp(unpack('<i',
                                                             f.read(4))[0])
        hdr['patient_id'], = unpack('<i', f.read(4))
        hdr['study_id'], = unpack('<i', f.read(4))
        hdr['pat_last_name'] = _make_str(unpack('c' * 80, f.read(80)))
        hdr['pat_first_name'] = _make_str(unpack('c' * 80, f.read(80)))
        hdr['pat_middle_name'] = _make_str(unpack('c' * 80, f.read(80)))
        hdr['patient_id'] = _make_str(unpack('c' * 80, f.read(80)))
        assert f.tell() == 352

        if hdr['file_schema'] >= 7:
            hdr['sample_freq'], = unpack('<d', f.read(8))
            n_chan, = unpack('<i', f.read(4))
            hdr['num_channels'] = n_chan
            hdr['deltabits'], = unpack('<i', f.read(4))
            hdr['phys_chan'] = unpack('<' + 'i' * hdr['num_channels'],
                                      f.read(hdr['num_channels'] * 4))

            f.seek(4464)
            hdr['headbox_type'] = unpack('<' + 'i' * 4, f.read(16))
            hdr['headbox_sn'] = unpack('<' + 'i' * 4, f.read(16))
            hdr['headbox_sw_version'] = _make_str(unpack('c' * 40, f.read(40)))
            hdr['dsp_hw_version'] = _make_str(unpack('c' * 10, f.read(10)))
            hdr['dsp_sw_version'] = _make_str(unpack('c' * 10, f.read(10)))
            hdr['discardbits'], = unpack('<i', f.read(4))

        if hdr['file_schema'] >= 8:
            hdr['shorted'] = unpack('<' + 'h' * 1024, f.read(2048))[:n_chan]
            hdr['frequency_factor'] = unpack('<' + 'h' * 1024,
							     f.read(2048))[:n_chan]

    return hdr


class Ktlx():
    def __init__(self, ktlx_dir):
        if isinstance(ktlx_dir, str):
            lg.info('Reading ' + ktlx_dir)
            self.filename = ktlx_dir
            self._hdr = self._read_hdr_dir()

    def _read_hdr_dir(self):
        """Read the header for basic information.

        Returns
        -------
        hdr : dict
          - 'erd': header of .erd file
          - 'stc': general part of .stc file
          - 'stamps' : time stamp for each file

        Also, it adds the attribute
        _basename : str
            the name of the files inside the directory

        """
        eeg_file = join(self.filename, basename(self.filename) + '.stc')
        if exists(eeg_file):
            self._basename = splitext(basename(self.filename))[0]
        else:  # if the folder was renamed
            eeg_file = glob(join(self.filename, '*.stc'))
            if len(eeg_file) == 1:
                self._basename = splitext(basename(eeg_file[0]))[0]
            elif len(eeg_file) == 0:
                raise FileNotFoundError('Could not find any .stc file.')
            else:
                raise OSError('Found too many .stc files: ' +
                              '\n'.join(eeg_file))

        hdr = {}

        # use .erd because it has extra info, such as sampling freq
        hdr['erd'] = _read_hdr_file(join(self.filename, self._basename +
                                         '.erd'))

        stc = _read_stc(join(self.filename, self._basename + '.stc'))
        hdr['stc'], hdr['stamps'] = stc

        return hdr

    def return_dat(self, chan, begsam, endsam):
        """Read the data based on begsam and endsam.

        Parameters
        ----------
        chan : list of int
            list of channel indeces
        begsam : int
            index of the first sample
        endsam :
            index of the last sample

        Returns
        -------
        ndarray
            2-d matrix with data (might contain NaN)

        Notes
        -----
        The sample numbering is not based on the samples in the files (i.e.
        the first sample of the first file is NOT the first sample of the
        dataset) because it depends on the stamps in the STC file. Usually, the
        recording starts and after a few millisecond (maybe one second), the
        actual acquisition starts. STC takes the offset into account. This has
        the counterintuitive result that if you call read_data, the first few
        hundreds samples are nan.

        """
        dat = empty((len(chan), endsam - begsam))
        dat.fill(NaN)

        stc, all_stamp = _read_stc(join(self.filename, self._basename +
                                        '.stc'))

        all_erd = [x['segment_name'] for x in all_stamp]
        all_beg = asarray([x['start_stamp'] for x in all_stamp])
        all_end = asarray([x['end_stamp'] for x in all_stamp])

        begrec = get_erd(begsam, all_beg, all_end)
        endrec = get_erd(endsam, all_beg, all_end)
        if begrec is None and endrec is None:
            return dat

        if begrec is None:
            begrec = 0
        if endrec is None:
            endrec = len(all_stamp) - 1

        lg.debug('Reading from recording #{} ({})'.format(begrec,
                                                          all_erd[begrec]) +
                 ' to recording #{} ({})'.format(endrec, all_erd[endrec]))

        for rec in range(begrec, endrec + 1):
            begpos_rec = begsam - all_stamp[rec]['start_stamp']
            if begpos_rec < 0:
                begpos_rec = 0

            endpos_rec = endsam - all_stamp[rec]['start_stamp']
            if endpos_rec > all_stamp[rec]['sample_span']:
                endpos_rec = all_stamp[rec]['sample_span']

            # this looks weird, but it takes into account whether the values
            # are outside of the limits of the file
            d1 = begpos_rec + all_stamp[rec]['start_stamp'] - begsam
            d2 = endpos_rec + all_stamp[rec]['start_stamp'] - begsam

            erd_file = join(self.filename, all_erd[rec] + '.erd')
            dat_rec = _read_erd(erd_file, all_stamp[rec]['sample_span'])
            lg.debug('From {}, selecting samples {}-{}'.format(all_erd[rec],
                                                               begpos_rec,
                                                               endpos_rec))
            dat[:, d1:d2] = dat_rec[chan, begpos_rec:endpos_rec]

        return dat

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
        # information contained in .erd
        orig = self._hdr['erd']
        if orig['patient_id']:
            subj_id = orig['patient_id']
        else:
            subj_id = (orig['pat_first_name'] + orig['pat_middle_name'] +
                       orig['pat_last_name'])

        start_time = orig['creation_time']
        s_freq = orig['sample_freq']

        # information contained in .stc
        n_samples = sum([x['sample_span'] for x in self._hdr['stamps']])

        # make a fake chan_name, it'll be replace if it exists
        try:
            ent_file = join(self.filename, self._basename + '.ent')
            if not exists(ent_file):
                ent_file = join(self.filename, self._basename + '.ent.old')
            ent_notes = _read_ent(ent_file)
        except FileNotFoundError:
            lg.warning('could not find .ent file, channels have arbitrary '
                       'names')
            chan_name = ['chan{0:03}'.format(x) for x in
                         range(orig['num_channels'])]
        else:
            for ent_note in ent_notes:
                try:
                    chan_name = _find_channels(ent_note['value'])
                    chan_name = chan_name[:orig['num_channels']]
                except:
                    continue
                else:
                    break

        try:
            orig['notes'] = self._read_notes()
        except FileNotFoundError:
            orig['notes'] = 'could not find .ent file'

        try:
            vtc_file = join(self.filename, self._basename + '.vtc')
            orig['vtc'] = _read_vtc(vtc_file)
        except FileNotFoundError:
            orig['vtc'] = None

        try:
            snc_file = join(self.filename, self._basename + '.snc')
            orig['snc'] = _read_snc(snc_file)
        except FileNotFoundError:
            orig['snc'] = None

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

    def _read_notes(self):
        """Reads the notes of the Ktlx recordings.

        However, this function formats the note already in the EDFBrowser
        format. Maybe the format should be more general.
        """
        ent_file = join(self.filename, self._basename + '.ent')
        if not exists(ent_file):
            ent_file = join(self.filename, self._basename + '.ent.old')

        ent_notes = _read_ent(ent_file)
        allnote = []
        for n in ent_notes:
            try:
                n['value'].keys()
                allnote.append(n['value'])
            except AttributeError:
                lg.debug('Note of length {} was not '
                         'converted to dict'.format(n['length']))

        s_freq = self._hdr['erd']['sample_freq']
        start_time = self._hdr['erd']['creation_time']
        pcname = '0CFEBE72-DA20-4b3a-A8AC-CDD41BFE2F0D'
        note_time = []
        note_name = []
        note_note = []
        for n in allnote:
            if n['Text'] == 'Analyzed Data Note':
                continue
            if not n['Text']:
                continue
            if 'User' not in n['Data'].keys():
                continue
            user1 = n['Data']['User'] == 'Persyst'
            user2 = n['Data']['User'] == 'eeg'
            user3 = n['Data']['User'] == pcname
            user4 = n['Data']['User'] == 'XLSpike - Intracranial'
            user5 = n['Data']['User'] == 'XLEvent - Intracranial'
            if user1 or user2 or user3 or user4 or user5:
                continue
            if len(n['Data']['User']) == 0:
                note_name.append('-unknown-')
            else:
                note_name.append(n['Data']['User'].split()[0])
            note_time.append(start_time +
                             timedelta(seconds=n['Stamp'] / s_freq))
            note_note.append(n['Text'])

        s = []
        for time, name, note in zip(note_time, note_name, note_note):
            s.append(datetime.strftime(time, '%Y-%m-%dT%H:%M:%S') +
                     ',' + '0' + ',' +  # zero duration
                     note + ' (' + name + ')')

        return '\n'.join(s)
