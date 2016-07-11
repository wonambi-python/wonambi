"""Package to import and export OpBox Physiology format.
"""
from datetime import datetime, timedelta
from pathlib import Path
from struct import unpack
from os import SEEK_END

from numpy import c_, empty, float64, NaN, memmap


N_HDR_BYTES = 12
BYTESIZE = float64().itemsize


class OpBox:
    """Class to read the data in opbox format, which is fast to write and read

    Parameters
    ----------
    filename : path to file
        the name of the filename with extension .phy
    """
    def __init__(self, filename):
        self.filename = filename

        self._n_samples = None
        self._n_chan_in_dat = None

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
        orig : empty list
            no additional info present
        """
        with open(self.filename, 'rb') as f:
            s_freq, n_anlg, n_dgtl = unpack('<iii', f.read(12))
            f.seek(0, SEEK_END)
            eof = f.tell()
        s_freq = float(s_freq)

        p = Path(self.filename)
        try:
            subj_id, date, time = p.stem.split('-')
            start_time = datetime.strptime(date + time, '%Y%m%d%H%M%S')
        except ValueError:
            # if it can't parse info from name, use arbitrary info
            subj_id = ''
            start_time = datetime(1900, 1, 1, 0, 0, 0)

        n_chan = n_anlg + n_dgtl
        n_chan_in_dat = n_chan + 1  # add timestamp

        n_samples = int((eof - N_HDR_BYTES) / n_chan_in_dat / BYTESIZE)

        chan_name = ['a{:03d}'.format(x) for x in range(n_anlg)]
        chan_name.extend(['d{:03d}'.format(x) for x in range(n_dgtl)])

        orig = []  # no additional info

        self._n_samples = n_samples
        self._n_chan_in_dat = n_chan_in_dat

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
            A 2d matrix, with dimension chan X samples. To save memory, the
            data are memory-mapped, and you cannot change the values on disk.
        """
        if isinstance(chan, int):  # make sure it's a list
            chan = [chan, ]

        data = memmap(self.filename, dtype='float64', mode='c',
                      shape=(self._n_chan_in_dat, self._n_samples), order='F',
                      offset=N_HDR_BYTES)
        data = data[1:, :]  # ignore timestamps

        begrec = max((begsam, 0))
        endrec = min((endsam, self._n_samples))
        dat = data[chan, begrec:endrec].astype(float64)

        if begsam < 0:
            pad = empty((dat.shape[0], 0 - begsam))
            pad.fill(NaN)
            dat = c_[pad, dat]

        if endsam >= self._n_samples:

            pad = empty((dat.shape[0], endsam - self._n_samples))
            pad.fill(NaN)
            dat = c_[dat, pad]

        return dat

    def return_markers(self):
        """This format doesn't have markers.

        Returns
        -------
        empty list

        Raises
        ------
        FileNotFoundError
            when it cannot read the events for some reason (don't use other
            exceptions).
        """
        return []
