from os import SEEK_SET, SEEK_END, SEEK_CUR
from datetime import datetime, date
from struct import unpack

from numpy import array, dtype, empty, fromfile, iinfo, memmap, NaN, pad

N_ZONES = 15
MAX_SAMPLE = 128
MAX_CAN_VIEW = 128


class Micromed:
    """Basic class to read Micromed data. Supports .TRC and .VWR files

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory
    """
    def __init__(self, filename):
        self.filename = filename
        self._header = {}

        with open(self.filename, 'rb') as f:
            self._header = _read_header(f)

            f.seek(0, SEEK_END)
            EOData = f.tell()

        self._bodata = self._header['BOData']
        self._n_chan = self._header['n_chan']
        self._n_bytes = self._header['n_bytes']
        self._s_freq = self._header['s_freq']
        self._n_smp = int((EOData - self._bodata) /
                          (self._n_chan * self._n_bytes))

        self._factors = array([ch['factor'] for ch in self._header['chans']])
        self._offset = array([ch['logical_ground'] for ch in self._header['chans']])

        self._triggers = self._header['trigger']
        self._videos = self._header['dvideo']

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

        subj_id = self._header['name'] + ' ' + self._header['surname']
        chan_name = [ch['chan_name'] for ch in self._header['chans']]

        return subj_id, self._header['start_time'], self._header['s_freq'], chan_name, self._n_smp, self._header

    def return_dat(self, chan, begsam, endsam):
        """Return the data as 2D numpy.ndarray.

        Parameters
        ----------
        chan : int or list
            index (indices) of the channels to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A 2d matrix, with dimension chan X samples
        """

        if type(chan) == int:  # if single value is provided it needs to be transformed to list to generate a 2d matrix
            chan = [chan, ]

        if (begsam >= self._n_smp) or (endsam < 0):
            dat = empty((len(chan), endsam - begsam))
            dat.fill(NaN)
            return dat

        if begsam < 0:
            begpad = -1 * begsam
            begsam = 0
        else:
            begpad = 0

        if endsam > self._n_smp:
            endpad = endsam - self._n_smp
            endsam = self._n_smp
        else:
            endpad = 0

        dshape = (self._n_chan, endsam - begsam)
        sig_dtype = 'u' + str(self._n_bytes)
        offset = self._bodata + begsam * self._n_bytes * self._n_chan
        dat = memmap(str(self.filename), dtype=sig_dtype, order='F', mode='r',
                     shape=dshape, offset=offset).astype('float')

        dat = pad(dat[chan, :], ((0, 0), (begpad, endpad)), mode='constant',
                  constant_values=NaN)

        return (dat - self._offset[chan, None]) * self._factors[chan, None]

    def return_markers(self):
        """Return all the markers (also called triggers or events).

        Returns
        -------
        list of dict
            where each dict contains 'name' as str, 'start' and 'end' as float
            in seconds from the start of the recordings, and 'chan' as list of
            str with the channels involved (if not of relevance, it's None).

        Raises
        ------
        FileNotFoundError
            when it cannot read the events for some reason (don't use other
            exceptions).
        """
        markers = []

        triggers = self._triggers
        DTYPE_MAX = iinfo(triggers.dtype['sample']).max
        triggers = triggers[triggers['sample'] != DTYPE_MAX]

        for trig in triggers:
            markers.append(
                {'name': str(trig['code']),
                 'start': trig['sample'] / self._s_freq,
                 'end': trig['sample'] / self._s_freq,
                 })

        return markers

    def return_videos(self, begtime, endtime):
        vid = self._videos

        # remove empty rows
        DTYPE_MAX = iinfo(vid.dtype['delay']).max
        vid = vid[vid['delay'] != DTYPE_MAX]

        if vid.shape[0] == 0:
            raise OSError('No videos for this dataset')

        if vid.shape[0] > 1:
            raise NotImplementedError('Currently it handles only one video.')

        # TODO: to test if delay is positive or negative
        video_beg = begtime + vid['delay'].item() / 1000
        video_end = endtime + vid['delay'].item() / 1000

        # full name without number
        video_name = 'VID_' + str(vid['file_ext'].item()) + '.AVI'

        mpgfiles = [
            str(self.filename.parent / video_name),
            ]

        return mpgfiles, video_beg, video_end


def _read_header(f):

    orig = {}

    orig['title'] = f.read(32).decode('utf-8').strip()
    orig['laboratory'] = f.read(32).strip(b'\x00').decode('utf-8').strip()

    # patient
    orig['surname'] = f.read(22).decode('utf-8').strip()
    orig['name'] = f.read(20).decode('utf-8').strip()
    month, day, year = unpack('bbb', f.read(3))
    orig['date_of_birth'] = date(year + 1900, month, day)
    f.seek(19, SEEK_CUR)

    # recording
    day, month, year, hour, minute, sec = unpack('bbbbbb', f.read(6))
    orig['start_time'] = datetime(year + 1900, month, day, hour, minute, sec)

    acquisition_unit_code = unpack('h', f.read(2))[0]
    orig['acquisition_unit'] = ACQUISITION_UNIT.get(acquisition_unit_code,
                                                    str(acquisition_unit_code))
    filetype_code = unpack('H', f.read(2))[0]
    orig['filetype'] = FILETYPE[filetype_code]

    orig['BOData'] = unpack('I', f.read(4))[0]
    orig['n_chan'] = unpack('H', f.read(2))[0]
    orig['multiplexer'] = unpack('H', f.read(2))[0]
    orig['s_freq'] = unpack('H', f.read(2))[0]
    orig['n_bytes'] = unpack('H', f.read(2))[0]
    orig['compression'] = unpack('H', f.read(2))[0]  # 0 non compression, 1 compression.
    orig['n_montages'] = unpack('H', f.read(2))[0]  # Montages : number of specific montages
    orig['dvideo_begin'] = unpack('I', f.read(4))[0]  # Starting sample of digital video
    orig['mpeg_delay'] = unpack('H', f.read(2))[0]  # Number of frames per hour of de-synchronization in MPEG acq

    f.seek(15, SEEK_CUR)
    header_type_code = unpack('b', f.read(1))[0]
    orig['header_type'] = HEADER_TYPE[header_type_code]

    zones = {}
    for _ in range(N_ZONES):
        zname, pos, length = unpack('8sII', f.read(16))
        zname = zname.decode('utf-8').strip()
        zones[zname] = pos, length

    pos, length = zones['ORDER']
    f.seek(pos, SEEK_SET)
    order = fromfile(f, dtype='u2', count=orig['n_chan'])

    chans = _read_labcod(f, zones['LABCOD'], order)

    pos, length = zones['NOTE']
    f.seek(pos, SEEK_SET)
    DTYPE = dtype([('sample', 'u4'), ('text', 'S40')])
    notes = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    pos, length = zones['FLAGS']
    f.seek(pos, SEEK_SET)
    DTYPE = dtype([('begin', 'u4'), ('end', 'u4')])
    flags = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    pos, length = zones['TRONCA']
    f.seek(pos, SEEK_SET)
    DTYPE = dtype([('time_in_samples', 'u4'), ('sample', 'u4')])
    segments = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    # impedance
    DTYPE = dtype([('positive', 'u1'), ('negative', 'u1')])
    pos, length = zones['IMPED_B']
    f.seek(pos, SEEK_SET)
    impedance_begin = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    pos, length = zones['IMPED_E']
    f.seek(pos, SEEK_SET)
    impedance_end = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    montage = _read_montage(f, zones['MONTAGE'])

    # if average has been computed
    pos, length = zones['COMPRESS']
    f.seek(pos, SEEK_SET)
    avg = {}
    avg['trace'], avg['file'], avg['prestim'], avg['poststim'], avg['type'] = unpack('IIIII', f.read(5 * 4))
    avg['free'] = f.read(108).strip(b'\x01\x00')

    history = _read_history(f, zones['HISTORY'])

    pos, length = zones['DVIDEO']
    f.seek(pos, 0)
    DTYPE = dtype([('delay', 'u4'), ('duration', 'u4'), ('file_ext', 'u4'), ('empty', 'u4')])
    dvideo = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    # events
    DTYPE = dtype([('code', 'u4'), ('begin', 'u4'), ('end', 'u4')])
    pos, length = zones['EVENT A']
    f.seek(pos, 0)
    event_a = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    pos, length = zones['EVENT B']
    f.seek(pos, 0)
    event_b = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    pos, length = zones['TRIGGER']
    DTYPE = dtype([('sample', 'u4'), ('code', 'u2')])
    f.seek(pos, 0)
    trigger = fromfile(f, dtype=DTYPE, count=int(length / DTYPE.itemsize))

    orig.update({
        'order': order,
        'chans': chans,
        'notes': notes,
        'flags': flags,
        'segments': segments,
        'impedance_begin': impedance_begin,
        'impedance_end': impedance_end,
        'montage': montage,
        'history': history,
        'dvideo': dvideo,
        'event_a': event_a,
        'event_b': event_b,
        'trigger': trigger,
        })

    return orig


ACQUISITION_UNIT = {
    0: 'BQ124 - 24 channels headbox, Internal Interface',
    2: 'MS40 - Holter recorder',
    6: 'BQ132S - 32 channels headbox, Internal Interface',
    7: 'BQ124 - 24 channels headbox, BQ CARD Interface',
    8: 'SAM32 - 32 channels headbox, BQ CARD Interface',
    9: 'SAM25 - 25 channels headbox, BQ CARD Interface',
    10: 'BQ132S R - 32 channels reverse headbox, Internal Interface',
    11: 'SAM32 R - 32 channels reverse headbox, BQ CARD Interface',
    12: 'SAM25 R - 25 channels reverse headbox, BQ CARD Interface',
    13: 'SAM32 - 32 channels headbox, Internal Interface',
    14: 'SAM25 - 25 channels headbox, Internal Interface',
    15: 'SAM32 R - 32 channels reverse headbox, Internal Interface',
    16: 'SAM25 R - 25 channels reverse headbox, Internal Interface',
    17: 'SD - 32 channels headbox with jackbox, SD CARD Interface -- PCI Internal Interface',
    18: 'SD128 - 128 channels headbox, SD CARD Interface -- PCI Internal Interface',
    19: 'SD96 - 96 channels headbox, SD CARD Interface -- PCI Internal Interface',
    20: 'SD64 - 64 channels headbox, SD CARD Interface -- PCI Internal Interface',
    21: 'SD128c - 128 channels headbox with jackbox, SD CARD Interface -- PCI Internal Interface',
    22: 'SD64c - 64 channels headbox with jackbox, SD CARD Interface -- PCI Internal Interface',
    23: 'BQ132S - 32 channels headbox, PCI Internal Interface',
    24: 'BQ132S R - 32 channels reverse headbox, PCI Internal Interface',
    }

FILETYPE = {
    40: 'C128 C.R., 128 EEG (headbox SD128 only)',
    42: 'C84P C.R., 84 EEG, 44 poly (headbox SD128 only)',
    44: 'C84 C.R., 84 EEG, 4 reference signals (named MKR,MKRB,MKRC,MKRD) (headbox SD128 only)',
    46: 'C96 C.R., 96 EEG (headbox SD128 -- SD96 -- BQ123S(r))',
    48: 'C63P C.R., 63 EEG, 33 poly',
    50: 'C63 C.R., 63 EEG, 3 reference signals (named MKR,MKRB,MKRC)',
    52: 'C64 C.R., 64 EEG',
    54: 'C42P C.R., 42 EEG, 22 poly',
    56: 'C42 C.R., 42 EEG, 2 reference signals (named MKR,MKRB)',
    58: 'C32 C.R., 32 EEG',
    60: 'C21P C.R., 21 EEG, 11 poly',
    62: 'C21 C.R., 21 EEG, 1 reference signal (named MKR)',
    64: 'C19P C.R., 19 EEG, variable poly',
    66: 'C19 C.R., 19 EEG, 1 reference signal (named MKR)',
    68: 'C12 C.R., 12 EEG',
    70: 'C8P C.R., 8 EEG, variable poly',
    72: 'C8 C.R., 8 EEG',
    74: 'CFRE C.R., variable EEG, variable poly',
    76: 'C25P C.R., 25 EEG (21 standard, 4 poly transformed to EEG channels), 7 poly -- headbox BQ132S(r) only',
    78: 'C27P C.R., 27 EEG (21 standard, 6 poly transformed to EEG channels), 5 poly -- headbox BQ132S(r) only',
    80: 'C24P C.R., 24 EEG (21 standard, 3 poly transformed to EEG channels), 8 poly -- headbox SAM32(r) only',
    82: 'C25P C.R., 25 EEG (21 standard, 4 poly transformed to EEG channels), 7 poly -- headbox SD with headbox JB 21P',
    84: 'C27P C.R., 27 EEG (21 standard, 6 poly transformed to EEG channels), 5 poly -- headbox SD with headbox JB 21P',
    86: 'C31P C.R., 27 EEG (21 standard, 10 poly transformed to EEG channels), 1 poly -- headbox SD with headbox JB 21P6',
    100: 'C26P C.R., 26 EEG, 6 poly (headbox SD, SD64c, SD128c with headbox JB Mini)',
    101: 'C16P C.R., 16 EEG, 16 poly (headbox SD with headbox JB M12)',
    102: 'C12P C.R., 12 EEG, 20 poly (headbox SD with headbox JB M12)',
    103: '32P 32 poly (headbox SD, SD64c, SD128c with headbox JB Bip)',
    120: 'C48P C.R., 48 EEG, 16 poly (headbox SD64)',
    121: 'C56P C.R., 56 EEG, 8 poly (headbox SD64)',
    122: 'C24P C.R., 24 EEG, 8 poly (headbox SD64)',
    140: 'C52P C.R., 52 EEG, 12 poly (headbox SD64c, SD128c with 2 headboxes JB Mini)',
    141: '64P 64 poly (headbox SD64c, SD128c with 2 headboxes JB Bip)',
    160: 'C88P C.R., 88 EEG, 8 poly (headbox SD96)',
    161: 'C80P C.R., 80 EEG, 16 poly (headbox SD96)',
    162: 'C72P C.R., 72 EEG, 24 poly (headbox SD96)',
    180: 'C120P C.R., 120 EEG, 8 poly (headbox SD128)',
    181: 'C112P C.R., 112 EEG, 16 poly (headbox SD128)',
    182: 'C104P C.R., 104 EEG, 24 poly (headbox SD128)',
    183: 'C96P C.R., 96 EEG, 32 poly (headbox SD128)',
    200: 'C122P C.R., 122 EEG, 6 poly (headbox SD128c with 4 headboxes JB Mini)',
    201: 'C116P C.R., 116 EEG, 12 poly (headbox SD128c with 4 headboxes JB Mini)',
    202: 'C110P C.R., 110 EEG, 18 poly (headbox SD128c with 4 headboxes JB Mini)',
    203: 'C104P C.R., 104 EEG, 24 poly (headbox SD128c with 4 headboxes JB Mini)',
    204: '128P 128 poly (headbox SD128c with 4 headboxes JB Bip)',
    205: '96P 96 poly (headbox SD128c with 3 headboxes JB Bip)',
    }

HEADER_TYPE = {
    0: 'Micromed "System 1" Header type',
    1: 'Micromed "System 1" Header type',
    2: 'Micromed "System 2" Header type',
    3: 'Micromed "System98" Header type',
    4: 'Micromed "System98" Header type',
    }

UNITS = {
    -1: 'nV',
    0: 'μV',
    1: 'mV',
    2: 'V',
    100: '%',
    101: 'bpm',
    102: 'dimentionless',
    }


def _read_labcod(f, zone, order):
    pos, length = zone
    CHAN_LENGTH = 128

    chans = []

    for i_ch in order:
        chan = {}

        f.seek(pos + i_ch * CHAN_LENGTH, 0)

        chan['status'] = f.read(1)  # Status of electrode for acquisition : 0 : not acquired, 1 : acquired
        chan['channelType'] = f.read(1)  # TODO: type of reference

        chan['chan_name'] = f.read(6).strip(b'\x01\x00').decode()
        chan['ground'] = f.read(6).strip(b'\x01\x00').decode()
        l_min, l_max, chan['logical_ground'], ph_min, ph_max = unpack('iiiii', f.read(20))
        chan['factor'] = float(ph_max - ph_min) / float(l_max - l_min + 1)

        k = unpack('h', f.read(2))[0]
        chan['units'] = UNITS.get(k, UNITS[0])

        chan['HiPass_Limit'], chan['HiPass_Type'] = unpack('HH', f.read(4))
        chan['LowPass_Limit'], chan['LowPass_Type'] = unpack('HH', f.read(4))

        chan['rate_coefficient'], chan['position'] = unpack('HH', f.read(4))
        chan['Latitude'], chan['Longitude'] = unpack('ff', f.read(8))
        chan['presentInMap'] = unpack('B', f.read(1))[0]
        chan['isInAvg'] = unpack('B', f.read(1))[0]
        chan['Description'] = f.read(32).strip(b'\x01\x00').decode()
        chan['xyz'] = unpack('fff', f.read(12))
        chan['Coordinate_Type'] = unpack('H', f.read(2))[0]
        chan['free'] = f.read(24).strip(b'\x01\x00')

        chans.append(chan)

    return chans


def _read_montage(f, zone):
    pos, length = zone
    f.seek(pos, SEEK_SET)

    montages = []

    while f.tell() < (pos + length):
        montage = {
            'lines': unpack('H', f.read(2))[0],
            'sectors': unpack('H', f.read(2))[0],
            'base_time': unpack('H', f.read(2))[0],
            'notch': unpack('H', f.read(2))[0],
            'colour': unpack(MAX_CAN_VIEW * 'B', f.read(MAX_CAN_VIEW)),
            'selection': unpack(MAX_CAN_VIEW * 'B', f.read(MAX_CAN_VIEW)),
            'description': f.read(64).strip(b'\x01\x00').decode(),
            'inputsNonInv': unpack(MAX_CAN_VIEW * 'H', f.read(MAX_CAN_VIEW * 2)),  # NonInv : non inverting input
            'inputsInv': unpack(MAX_CAN_VIEW * 'H', f.read(MAX_CAN_VIEW * 2)),  # Inv : inverting input

            'HiPass_Filter': unpack(MAX_CAN_VIEW * 'I', f.read(MAX_CAN_VIEW * 4)),
            'LowPass_Filter': unpack(MAX_CAN_VIEW * 'I', f.read(MAX_CAN_VIEW * 4)),
            'reference': unpack(MAX_CAN_VIEW * 'I', f.read(MAX_CAN_VIEW * 4)),
            'free': f.read(1720).strip(b'\x01\x00'),
            }
        montages.append(montage)

    return montages


def _read_history(f, zone):
    """This matches the Matlab reader from Matlab Exchange but doesn't seem
    correct.
    """
    pos, length = zone
    f.seek(pos, SEEK_SET)

    histories = []
    while f.tell() < (pos + length):
        history = {
            'nSample': unpack(MAX_SAMPLE * 'I', f.read(MAX_SAMPLE * 4)),
            'lines': unpack('H', f.read(2)),
            'sectors': unpack('H', f.read(2)),
            'base_time': unpack('H', f.read(2)),
            'notch': unpack('H', f.read(2)),
            'colour': unpack(MAX_CAN_VIEW * 'B', f.read(MAX_CAN_VIEW)),
            'selection': unpack(MAX_CAN_VIEW * 'B', f.read(MAX_CAN_VIEW)),
            'description': f.read(64).strip(b'\x01\x00'),
            'inputsNonInv': unpack(MAX_CAN_VIEW * 'H', f.read(MAX_CAN_VIEW * 2)),  # NonInv : non inverting input
            'inputsInv': unpack(MAX_CAN_VIEW * 'H', f.read(MAX_CAN_VIEW * 2)),  # Inv : inverting input

            'HiPass_Filter': unpack(MAX_CAN_VIEW * 'I', f.read(MAX_CAN_VIEW * 4)),
            'LowPass_Filter': unpack(MAX_CAN_VIEW * 'I', f.read(MAX_CAN_VIEW * 4)),
            'reference': unpack(MAX_CAN_VIEW * 'I', f.read(MAX_CAN_VIEW * 4)),
            'free': f.read(1720).strip(b'\x01\x00'),
            }
        histories.append(history)

    return histories
