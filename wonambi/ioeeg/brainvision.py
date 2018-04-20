from os import SEEK_CUR, SEEK_SET, SEEK_END
from re import search, finditer, match
from datetime import datetime

from numpy import (fromfile,
                   fromstring,
                   asmatrix,
                   array,
                   arange,
                   c_,
                   diff,
                   empty,
                   hstack,
                   ndarray,
                   NaN,
                   vstack,
                   where,
                   dtype,
                   float64,
                   int32,
                   uint8,
                   )


class BrainVision:
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

        Notes
        -----
        As far as I can, BCI2000 doesn't have channel labels, so we use dummies
        starting at chan001 (more consistent with Matlab 1-base indexing...)
        """
        orig = {}
        orig = _read_header(self.filename)

        nchan = int(orig['SourceCh'])
        chan_name = ['ch{:03d}'.format(i + 1) for i in range(nchan)]
        chan_dtype = dtype(orig['DataFormat'])
        self.statevector_len = int(orig['StatevectorLen'])

        s_freq = int(orig['Parameter']['SamplingRate'])
        storagetime = orig['Parameter']['StorageTime'].replace('%20', ' ')
        try:  # newer version
            start_time = datetime.strptime(storagetime, '%a %b %d %H:%M:%S %Y')
        except:
            start_time = datetime.strptime(storagetime, '%Y-%m-%dT%H:%M:%S')

        subj_id = orig['Parameter']['SubjectName']

        self.dtype = dtype([(chan, chan_dtype) for chan in chan_name]
                            + [('statevector', 'S', self.statevector_len)])

        # compute n_samples based on file size - header
        with open(self.filename, 'rb') as f:
            f.seek(0, SEEK_END)
            EOData = f.tell()
        n_samples = int((EOData - int(orig['HeaderLen'])) / self.dtype.itemsize)

        self.s_freq = s_freq
        self.header_len = int(orig['HeaderLen'])
        self.n_samples = n_samples
        self.statevectors = _prepare_statevectors(orig['StateVector'])
        # TODO: a better way to parse header
        self.gain = array([float(x) for x in orig['Parameter']['SourceChGain'].split(' ')[1:]])

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
        """
        dat_begsam = max(begsam, 0)
        dat_endsam = min(endsam, self.n_samples)
        dur = dat_endsam - dat_begsam

        dtype_onlychan = dtype({k: v for k, v in self.dtype.fields.items() if v[0].kind != 'S'})

        # make sure we read some data at least, otherwise segfault
        if dat_begsam < self.n_samples and dat_endsam > 0:

            with self.filename.open('rb') as f:
                f.seek(self.header_len, SEEK_SET)  # skip header

                f.seek(self.dtype.itemsize * dat_begsam, SEEK_CUR)
                dat = fromfile(f, dtype=self.dtype, count=dur)

            dat = ndarray(dat.shape, dtype_onlychan, dat, 0, dat.strides).view((dtype_onlychan[0], len(dtype_onlychan.names))).T

        else:
            n_chan = len(dtype_onlychan.names)
            dat = empty((n_chan, 0))

        if begsam < 0:

            pad = empty((dat.shape[0], 0 - begsam))
            pad.fill(NaN)
            dat = c_[pad, dat]

        if endsam >= self.n_samples:

            pad = empty((dat.shape[0], endsam - self.n_samples))
            pad.fill(NaN)
            dat = c_[dat, pad]

        return dat[chan, :] * self.gain[chan][:, None]  # apply gain

    def return_markers(self, state='MicromedCode'):
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
        try:
            all_states = self._read_states()
        except ValueError:  # cryptic error when reading states
            return markers

        try:
            x = all_states[state]
        except KeyError:
            return markers

        markers = []
        i_mrk = hstack((0, where(diff(x))[0] + 1, len(x)))
        for i0, i1 in zip(i_mrk[:-1], i_mrk[1:]):
            marker = {'name': str(x[i0]),
                      'start': (i0) / self.s_freq,
                      'end': i1 / self.s_freq,
                     }
            markers.append(marker)

        return markers


def _read_header(vhdr_file):
    """

    TODO
    ----
    Parse section after [Comment]
    """
    hdr = {}
    with vhdr_file.open('r') as f:

        line = f.readline().strip()
        if line == 'Brain Vision Data Exchange Header File Version 1.0':
            hdr['version'] = 1.0
        elif line == 'Brain Vision Data Exchange Header File Version 2.0':
            hdr['version'] = 2.0
        else:
            raise ValueError(f'Unknown version "{line}"')

        for line in f:
            if line.startswith(';') or line == '\n':
                continue

            if line == '[Comment]\n':
                break

            if line.startswith('['):
                group = line.strip()[1:-1]
                hdr[group] = {}
                continue

            if '=' in line:
                k, v = line.strip().split('=')
                if ',' in v:
                    v = v.split(',')
                hdr[group][k] = v

    return hdr
