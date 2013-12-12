"""Module reads and writes header and data for EDF data.

Poor man's version of
https://github.com/breuderink/eegtools/blob/master/eegtools/io/edfplus.py

TODO: values are slightly different from those computed by fieldtrip

"""

from __future__ import division
from datetime import datetime
from re import findall
from math import floor
from numpy import empty, asarray, fromstring


def _assert_all_the_same(items):
    """Check that all the items in a list are the same.

    """
    assert all(items[0] == x for x in items)


class Edf:
    """Provide class EDF, which can be used to read the header and the data.

    Parameters
    ----------
    edffile : str
        Full path for the EDF file

    Attributes
    ----------
    h : dict
        disorganized header information

    """

    def __init__(self, edffile):
        if isinstance(edffile, str):
            self.filename = edffile
            self._read_hdr()

    def _read_hdr(self):
        """Read header from EDF file.

        It only reads the header for internal purposes and adds a hdr.

        """

        with open(self.filename, 'rb') as f:

            hdr = {}
            assert f.tell() == 0
            assert f.read(8) == b'0       '

            # recording info
            hdr['subject_id'] = f.read(80).decode('utf-8').strip()
            hdr['recording_id'] = f.read(80).decode('utf-8').strip()

            # parse timestamp
            (day, month, year) = [int(x) for x in findall('(\d+)',
                                  f.read(8).decode('utf-8'))]
            (hour, minute, sec) = [int(x) for x in findall('(\d+)',
                                   f.read(8).decode('utf-8'))]
            hdr['start_time'] = datetime(year + 2000, month, day, hour, minute,
                sec)

            # misc
            hdr['header_n_bytes'] = int(f.read(8))
            f.seek(44, 1)  # reserved for EDF+
            hdr['n_records'] = int(f.read(8))
            hdr['record_length'] = float(f.read(8))  # in seconds
            nchannels = hdr['n_channels'] = int(f.read(4))

            # read channel info
            channels = range(hdr['n_channels'])
            hdr['label'] = [f.read(16).decode('utf-8').strip() for n in
                            channels]
            hdr['transducer'] = [f.read(80).decode('utf-8').strip()
                                    for n in channels]
            hdr['physical_dim'] = [f.read(8).decode('utf-8').strip() for n in
                                    channels]
            hdr['physical_min'] = asarray([float(f.read(8))
                                            for n in channels])
            hdr['physical_max'] = asarray([float(f.read(8))
                                            for n in channels])
            hdr['digital_min'] = asarray([float(f.read(8)) for n in channels])
            hdr['digital_max'] = asarray([float(f.read(8)) for n in channels])
            hdr['prefiltering'] = [f.read(80).decode('utf-8').strip()
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

        """

        subj_id = self.hdr['subject_id']
        start_time = self.hdr['start_time']
        _assert_all_the_same(self.hdr['n_samples_per_record'])
        s_freq = (self.hdr['n_samples_per_record'][0] /
            self.hdr['record_length'])
        chan_name = self.hdr['label']
        n_samples = (self.hdr['n_samples_per_record'][0] *
            self.hdr['n_records'])

        return subj_id, start_time, s_freq, chan_name, n_samples, self.hdr

    def _read_dat(self, i_chan, begsam, endsam):
        """Read raw data from a single EDF channel.

        Reads only one channel at the time. Very initial implementation, very
        simple and probably not very fast

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

        assert begsam < endsam

        begsam = float(begsam)
        endsam = float(endsam)

        n_sam_rec = self.hdr['n_samples_per_record']

        begrec = int(floor(begsam / n_sam_rec[i_chan]))
        begsam_rec = int(begsam % n_sam_rec[i_chan])

        endrec = int(floor(endsam / n_sam_rec[i_chan]))
        endsam_rec = int(endsam % n_sam_rec[i_chan])

        dat = empty(shape=(endsam - begsam), dtype='int16')
        i_dat = 0

        with open(self.filename, 'rb') as f:
            for rec in range(begrec, endrec + 1):
                if rec == begrec:
                    begpos_rec = begsam_rec
                else:
                    begpos_rec = 0

                if rec == endrec:
                    endpos_rec = endsam_rec
                else:
                    endpos_rec = n_sam_rec[i_chan]

                begpos = begpos_rec + sum(n_sam_rec) * rec + sum(
                    n_sam_rec[:i_chan])
                endpos = endpos_rec + sum(n_sam_rec) * rec + sum(
                    n_sam_rec[:i_chan])

                f.seek(begpos * 2 + self.hdr['header_n_bytes'])
                samples = f.read(2 * (endpos - begpos))

                i_dat_end = i_dat + endpos - begpos
                dat[i_dat:i_dat_end] = fromstring(samples, dtype='<i2')
                i_dat = i_dat_end

        return dat

    def return_dat(self, chan, begsam, endsam):
        """Read data from an EDF file.

        Reads channel by channel, and adjusts the values by calibration.

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
            A 2d matrix, where the first dimension is the data and the second
            dimension are the channels

        """

        if isinstance(chan, int):
            chan = [chan]

        hdr = self.hdr
        dig_min = hdr['digital_min']
        phys_min = hdr['physical_min']
        phys_range = hdr['physical_max'] - hdr['physical_min']
        dig_range = hdr['digital_max'] - hdr['digital_min']
        assert all(phys_range > 0)
        assert all(dig_range > 0)
        gain = phys_range / dig_range

        dat = empty(shape=(len(chan), endsam - begsam), dtype='float32')

        for i, i_chan in enumerate(chan):
            d = self._read_dat(i_chan, begsam, endsam)
            dat[i, :] = (d - dig_min[i_chan]) * gain[i_chan] + phys_min[i_chan]

        return dat
