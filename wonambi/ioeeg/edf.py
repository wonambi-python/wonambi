"""Module reads and writes header and data for EDF data.
"""
from logging import getLogger

from datetime import datetime, timedelta, time, date
from pathlib import Path
from re import findall, finditer
from struct import pack

from numpy import (abs,
                   asarray,
                   empty,
                   fromfile,
                   iinfo,
                   ones,
                   max,
                   NaN,
                   newaxis,
                   repeat,
                   )

from .utils import decode, _select_blocks, DEFAULT_DATETIME

lg = getLogger(__name__)

EDF_FORMAT = 'int16'  # by definition
edf_iinfo = iinfo(EDF_FORMAT)
N_BYTES = edf_iinfo.dtype.itemsize
DIGITAL_MAX = edf_iinfo.max
DIGITAL_MIN = -1 * edf_iinfo.max  # so that digital 0 = physical 0

ANNOT_NAME = 'EDF Annotations'
PATTERN = b'(?P<onset>[+\-]\d+(?:\.\d*)?)(?:\x15(?P<duration>\d+(?:\.\d*)?))?(\x14(?P<annotation>[^\x00]*))?(?:\x14\x00)'


class Edf:
    """Provide class EDF, which can be used to read the header and the data.

    Parameters
    ----------
    edffile : str
        Full path for the EDF file

    Attributes
    ----------
    hdr : dict
        header taken from EDF file
    """
    def __init__(self, edffile):
        self.filename = Path(edffile)
        self._read_hdr()

    def _read_hdr(self):
        """Read header from EDF file.

        It only reads the header for internal purposes and adds a hdr.
        """
        with self.filename.open('rb') as f:

            hdr = {}
            assert f.tell() == 0
            assert f.read(8) == b'0       '

            # recording info
            hdr['subject_id'] = decode(f.read(80)).strip()
            hdr['recording_id'] = decode(f.read(80)).strip()

            # parse timestamp
            date_str = decode(f.read(8)).strip()

            if date_str == '':
                edf_date = DEFAULT_DATETIME.date()
            else:
                (day, month, year) = [int(x) for x in findall('(\d+)', date_str)]
                # Y2K: cutoff is 1985
                if year >= 85:
                    year += 1900
                else:
                    year += 2000
                edf_date = date(year, month, day)

            time_str = decode(f.read(8)).strip()
            if time_str == '':
                edf_time = DEFAULT_DATETIME.time()
            else:
                (hour, minute, day) = [int(x) for x in findall('(\d+)', time_str)]

                edf_time = time(hour, minute, day)

            hdr['start_time'] = datetime.combine(edf_date, edf_time)

            # misc
            hdr['header_n_bytes'] = int(f.read(8))
            f.seek(44, 1)  # reserved for EDF+
            hdr['n_records'] = int(f.read(8))
            hdr['record_length'] = float(f.read(8))  # in seconds
            nchannels = hdr['n_channels'] = int(f.read(4))

            # read channel info
            channels = range(hdr['n_channels'])
            hdr['label'] = [decode(f.read(16)).strip() for n in
                            channels]
            hdr['transducer'] = [decode(f.read(80)).strip()
                                 for n in channels]
            hdr['physical_dim'] = [decode(f.read(8)).strip() for n in
                                   channels]
            hdr['physical_min'] = [float(f.read(8)) for n in channels]
            hdr['physical_max'] = [float(f.read(8)) for n in channels]
            hdr['digital_min'] = [float(f.read(8)) for n in channels]
            hdr['digital_max'] = [float(f.read(8)) for n in channels]
            hdr['prefiltering'] = [decode(f.read(80)).strip()
                                   for n in channels]
            hdr['n_samples_per_record'] = [int(f.read(8)) for n in channels]
            f.seek(32 * nchannels, 1)  # reserved

            assert f.tell() == hdr['header_n_bytes']

            self.hdr = hdr

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

        Notes
        -----
        EDF+ accepts multiple frequency rates for different channels. Here, we
        use only the highest sampling frequency (normally used for EEG and MEG
        signals), and we UPSAMPLE all the other channels.
        """
        try:
            self.i_annot = self.hdr['label'].index(ANNOT_NAME)
        except ValueError:
            self.i_annot = None

        self.smp_in_blk = sum(self.hdr['n_samples_per_record'])

        self.max_smp = max(self.hdr['n_samples_per_record'])
        n_blocks = self.hdr['n_records']
        self.blocks = ones(n_blocks, dtype='int') * self.max_smp

        self.dig_min = asarray(self.hdr['digital_min'])
        self.phys_min = asarray(self.hdr['physical_min'])
        phys_range = asarray(self.hdr['physical_max']) - self.phys_min
        dig_range = asarray(self.hdr['digital_max']) - self.dig_min
        assert all(phys_range > 0)
        assert all(dig_range > 0)
        self.gain = phys_range / dig_range

        subj_id = self.hdr['subject_id']
        start_time = self.hdr['start_time']
        s_freq = self.max_smp / self.hdr['record_length']
        chan_name = [label for label in self.hdr['label'] if label != ANNOT_NAME]
        n_samples = self.max_smp * self.hdr['n_records']

        return subj_id, start_time, s_freq, chan_name, n_samples, self.hdr

    def return_dat(self, chan, begsam, endsam):
        """Read data from an EDF file.

        Reads channel by channel, and adjusts the values by calibration.

        Parameters
        ----------
        chan : list of int
            index (indices) of the channels to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A 2d matrix, where the first dimension is the channels and the
            second dimension are the samples.
        """
        assert begsam < endsam

        dat = empty((len(chan), endsam - begsam))
        dat.fill(NaN)

        with self.filename.open('rb') as f:

            for i_dat, blk, i_blk in _select_blocks(self.blocks, begsam, endsam):
                dat_in_rec = self._read_record(f, blk, chan)
                dat[:, i_dat[0]:i_dat[1]] = dat_in_rec[:, i_blk[0]:i_blk[1]]

        # calibration
        dat = ((dat.astype('float64') - self.dig_min[chan, newaxis]) *
               self.gain[chan, newaxis] + self.phys_min[chan, newaxis])

        return dat

    def _read_record(self, f, blk, chans):
        """Read raw data from a single EDF channel.

        Parameters
        ----------
        i_chan : int
            index of the channel to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A vector with the data as written on file, in 16-bit precision
        """
        dat_in_rec = empty((len(chans), self.max_smp))

        i_ch_in_dat = 0
        for i_ch in chans:
            offset, n_smp_per_chan = self._offset(blk, i_ch)

            f.seek(offset)
            x = fromfile(f, count=n_smp_per_chan, dtype=EDF_FORMAT)

            ratio = int(self.max_smp / n_smp_per_chan)
            dat_in_rec[i_ch_in_dat, :] = repeat(x, ratio)
            i_ch_in_dat += 1

        return dat_in_rec

    def _offset(self, blk, i_ch):
        ch_in_rec = sum(self.hdr['n_samples_per_record'][:i_ch])
        n_smp_per_chan = self.hdr['n_samples_per_record'][i_ch]
        offset_in_blk = self.smp_in_blk * blk + ch_in_rec
        offset = self.hdr['header_n_bytes'] + offset_in_blk * N_BYTES

        return offset, n_smp_per_chan

    def return_markers(self):
        """"""
        if self.i_annot is None:
            return []

        annotations = []
        with self.filename.open('rb') as f:
            for blk in range(self.hdr['n_records']):
                offset, n_smp_per_chan = self._offset(blk, self.i_annot)
                f.seek(offset)
                annotations.extend(_read_tal(f.read(n_smp_per_chan)))

        markers = []
        for annot in annotations:
            for name in annot['annotation']:
                m = {'name': name,
                     'start': annot['onset'],
                     'end': annot['onset'] + annot['dur'],
                     'chan': None,
                     }
                markers.append(m)

        return markers


def write_edf(data, filename, subj_id='X X X X', physical_max=1000):
    """Export data to FieldTrip.

    Parameters
    ----------
    data : instance of ChanTime
        data with only one trial
    filename : path to file
        file to export to (include '.mat')
    subj_id : str
        subject id
    physical_max : int
        values above this parameter will be considered saturated (and also
        those that are too negative). This parameter defines the precision.

    Notes
    -----
    Data is always recorded as 2 Byte int (which is 'int16'), so precision is
    limited. You can control the precision with physical_max. To get the
    precision:

    >>> precision = physical_max / DIGITAL_MAX

    where DIGITAL_MAX is 32767.
    """
    if data.start_time is None:
        raise ValueError('Data should contain a valid start_time (as datetime)')
    start_time = data.start_time + timedelta(seconds=data.axis['time'][0][0])

    if physical_max is None:
        physical_max = max(abs(data.data[0]))

    precision = physical_max / DIGITAL_MAX
    lg.info('Data exported to EDF will have precision ' + str(precision))

    physical_min = -1 * physical_max
    dat = data.data[0] / physical_max * DIGITAL_MAX
    dat = dat.astype(EDF_FORMAT)
    dat[dat > DIGITAL_MAX] = DIGITAL_MAX
    dat[dat < DIGITAL_MIN] = DIGITAL_MIN

    with open(filename, 'wb') as f:
        f.write('{:<8}'.format(0).encode('ascii'))
        f.write('{:<80}'.format(subj_id).encode('ascii'))  # subject_id
        f.write('{:<80}'.format('Startdate X X X X').encode('ascii'))
        f.write(start_time.strftime('%d.%m.%y').encode('ascii'))
        f.write(start_time.strftime('%H.%M.%S').encode('ascii'))

        n_smp = data.data[0].shape[1]
        s_freq = int(data.s_freq)
        n_records = n_smp // s_freq  # floor
        record_length = 1
        n_channels = data.number_of('chan')[0]

        header_n_bytes = 256 + 256 * n_channels
        f.write('{:<8d}'.format(header_n_bytes).encode('ascii'))
        f.write((' ' * 44).encode('ascii'))  # reserved for EDF+

        f.write('{:<8}'.format(n_records).encode('ascii'))
        f.write('{:<8d}'.format(record_length).encode('ascii'))
        f.write('{:<4}'.format(n_channels).encode('ascii'))

        for chan in data.axis['chan'][0]:
            f.write('{:<16}'.format(chan).encode('ascii'))  # label
        for _ in range(n_channels):
            f.write(('{:<80}').format('').encode('ascii'))  # tranducer
        for _ in range(n_channels):
            f.write('{:<8}'.format('uV').encode('ascii'))  # physical_dim
        for _ in range(n_channels):
            f.write('{:<8}'.format(physical_min).encode('ascii'))
        for _ in range(n_channels):
            f.write('{:<8}'.format(physical_max).encode('ascii'))
        for _ in range(n_channels):
            f.write('{:<8}'.format(DIGITAL_MIN).encode('ascii'))
        for _ in range(n_channels):
            f.write('{:<8}'.format(DIGITAL_MAX).encode('ascii'))
        for _ in range(n_channels):
            f.write('{:<80}'.format('').encode('ascii'))  # prefiltering
        for _ in range(n_channels):
            f.write('{:<8d}'.format(s_freq).encode('ascii'))  # n_smp in record
        for _ in range(n_channels):
            f.write((' ' * 32).encode('ascii'))

        length_record = s_freq * n_channels  # length of one record
        for i in range(n_records):
            i0 = i * s_freq
            i1 = i0 + s_freq
            x = dat[:, i0:i1].flatten(order='C')  # assumes it's ChanTimeData
            f.write(pack('<' + 'h' * length_record, *x))


def _read_tal(rawbytes):
    """Read TAL (Time-stamped Annotations Lists) using regex

    Parameters
    ----------
    rawbytes : bytes
        raw information from file

    Returns
    -------
    annotation : list of dict
        where each dict contains onset, duration, and list with the annotations
    """
    annotations = []

    for m in finditer(PATTERN, rawbytes):
        d = m.groupdict()
        annot = {'onset': float(decode(d['onset'])),
                 'dur': float(decode(d['duration'])) if d['duration'] else 0.,
                 'annotation': [decode(a) for a in d['annotation'].split(b'\x14') if a],
                 }

        if annot['annotation']:
            annotations.append(annot)

    return annotations


def remove_datetime(filename):
    """Remove datetime from filename by overwriting the date / time info.

    Parameters
    ----------
    filename : Path
        path to edf file

    Notes
    -----
    It modifies the file.

    TODO
    ----
    This function might be part of a large anonymization procedure for edf
    """
    with Path(filename).open('r+b') as f:
        f.seek(168)
        f.write(16 * b' ')
