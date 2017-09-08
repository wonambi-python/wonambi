from os import SEEK_SET, SEEK_END
from datetime import datetime
from struct import unpack

from numpy import fromfile

units = {-1: -1e9,  # nV
         0: -1e6,  # uV,
         1: -1e3,  # mV
         2: 1,
         100: 100,  # percent
         101: 1,  # dimentionless
         102: 1,  # dimentionless
        }

class Micromed:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory
    """
    def __init__(self, filename):
        self.filename = filename

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
        N_ZONES = 15
        orig = {}

        with self.filename.open('rb') as f:

            f.seek(64, SEEK_SET)
            orig['surname'] = f.read(22).decode('utf-8').strip()
            orig['name'] = f.read(20).decode('utf-8').strip()
            subj_id = orig['name'] + ' ' + orig['surname']

            f.seek(128, SEEK_SET)
            day, month, year, hour, minute, sec = unpack('bbbbbb', f.read(6))
            start_time = datetime(year + 1900, month, day, hour, minute, sec)

            f.seek(138, SEEK_SET)
            BOData, n_chan, Multiplexer, s_freq, N_BYTES = unpack('IHHHH', f.read(12))

            f.seek(175, SEEK_SET)
            hdr_version = unpack('b', f.read(1))[0]
            assert hdr_version == 4

            zones = {}
            for _ in range(N_ZONES):
                zname, pos, length = unpack('8sII', f.read(16))
                zname = zname.decode('utf-8').strip()
                zones[zname] = pos, length

            pos, length = zones['ORDER']
            f.seek(pos, 0)
            order = fromfile(f, dtype='u2', count=n_chan)

            f.seek(0, SEEK_END)
            EOData = f.tell()
            n_samples = int((EOData - BOData) / (n_chan * N_BYTES))
            self.n_smp = n_samples

            chan_name =  _read_channels(f, n_chan, order, zones)[0]

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

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

        TODO
        ----
        Write a reader from MICROMED data.
        """
        if begsam < 0:
            begpad = -1 * begsam
            begsam = 0
        else:
            begpad = 0

        if endsam > self.n_smp:
            endpad = endsam - self.n_smp
            endsam = self.n_smp
        else:
            endpad = 0

        return None

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
        return markers


def _read_channels(f, n_chan, order, zones):
    chan_names = []
    all_s_freq = []

    for c in range(n_chan):
        pos, length = zones['LABCOD']
        f.seek(pos + order[c] * 128, 0)

        chan_name = f.read(6).strip(b'\x01\x00').decode()
        chan_names.append(chan_name)
        ground = f.read(6).strip(b'\x01\x00').decode()

        logical_min, logical_max, logical_ground, physical_min, physical_max = unpack('iiiii', f.read(20))
        factor = float(physical_max - physical_min) / float( logical_max - logical_min + 1)

        k = unpack('h', f.read(2))[0]
        if k in units.keys():
            unit = units[k]
        else:
            unit = units[0]

        f.seek(8, 1)
        s_rate = unpack('H', f.read(2))[0]
        all_s_freq.append(s_rate)

        # signal = (rawdata[:, c].astype('f') - logical_ground) * factor * unit
    return chan_names,  factor, unit, all_s_freq
