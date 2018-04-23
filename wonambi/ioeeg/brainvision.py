from datetime import datetime

from numpy import (dtype,
                   memmap,
                   array,
                   c_,
                   empty,
                   NaN,
                   float64,
                   )


BV_ORIENTATION = {
    'MULTIPLEXED': 'F',
    'VECTORIZED': 'C',
    }

BV_DATATYPE = {
    'INT_16': 'int16',
    'INT_32': 'int32',
    'INT_64': 'int64',
    'IEEE_FLOAT_32': 'float32',
    'IEEE_FLOAT_64': 'float64',
    }


class BrainVision:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    Notes
    -----
    It should be .vhdr (because that file contains the pointer to the data). If
    it points to .eeg, we convert to .vhdr in any case.
    """
    def __init__(self, filename):
        self.filename = filename.with_suffix('.vhdr')

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
        subj_id = ''  # no subject information in the header

        hdr = _parse_ini(self.filename)

        self.eeg_file = self.filename.parent / hdr['Common Infos']['DataFile']
        self.vmrk_file = self.filename.parent / hdr['Common Infos']['MarkerFile']
        self.mrk = _parse_ini(self.vmrk_file)

        start_time = _read_datetime(self.mrk)
        self.s_freq = 1e6 / float(hdr['Common Infos']['SamplingInterval'])
        chan_name = [v[0] for v in hdr['Channel Infos'].values()]
        self.gain = array([float(v[2]) for v in hdr['Channel Infos'].values()])

        # number of samples
        self.data_type = BV_DATATYPE[hdr['Binary Infos']['BinaryFormat']]
        N_BYTES = dtype(self.data_type).itemsize
        n_samples = int(self.eeg_file.stat().st_size / N_BYTES / len(chan_name))

        self.dshape = len(chan_name), int(n_samples)
        self.data_order = BV_ORIENTATION[hdr['Common Infos']['DataOrientation']]

        orig = {
            'vhdr': hdr,
            'vmrk': self.mrk,
            }

        return subj_id, start_time, self.s_freq, chan_name, n_samples, orig

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
        dat = _read_memmap(self.eeg_file, self.dshape, begsam, endsam,
                           self.data_type, self.data_order)

        return dat[chan, :] * self.gain[chan, None]

    def return_markers(self):
        """Return all the markers (also called triggers or events).

        Returns
        -------
        list of dict
            where each dict contains 'name' as str, 'start' and 'end' as float
            in seconds from the start of the recordings, and 'chan' as list of
            str with the channels involved (if not of relevance, it's None).
        """
        markers = []
        for v in self.mrk['Marker Infos'].values():
            if v[0] == 'New Segment':
                continue

            markers.append({
                'name': v[1],
                'start': float(v[2]) / self.s_freq,
                'end': (float(v[2]) + float(v[3])) / self.s_freq,
                })

        return markers


def _parse_ini(brainvision_file):
    """

    TODO
    ----
    Parse section after [Comment]
    """
    ini = {}
    with brainvision_file.open('rb') as f:

        line = f.readline().decode('ascii').strip()
        if (line == 'Brain Vision Data Exchange Header File Version 1.0' or
           line == 'Brain Vision Data Exchange Marker File, Version 1.0'):

            ini['version'] = 1.0
            encoding = 'latin1'

        elif (line == 'Brain Vision Data Exchange Header File Version 2.0' or
              line == 'Brain Vision Data Exchange Marker File, Version 2.0'):
            ini['version'] = 2.0
            encoding = 'utf-8'

        else:
            raise ValueError(f'Unknown version "{line}"')

        for line in f:
            line = line.decode(encoding).strip()
            if line.startswith(';') or line == '':
                continue

            if line == '[Comment]':
                ini['Comment'] = f.read().decode(encoding)
                break

            if line.startswith('['):
                group = line[1:-1]
                ini[group] = {}
                continue

            if '=' in line:
                k, v = line.split('=')
                if ',' in v:
                    v = v.split(',')
                ini[group][k] = v

                # Use explicit encoding if it's in the header
                if k == 'Codepage':
                    encoding = v

    return ini


def _read_memmap(filename, dat_shape, begsam, endsam, datatype='double',
                 data_order='F'):

    n_samples = dat_shape[1]

    data = memmap(str(filename), dtype=datatype, mode='c',
                  shape=dat_shape, order=data_order)
    dat = data[:, max((begsam, 0)):min((endsam, n_samples))].astype(float64)

    if begsam < 0:

        pad = empty((dat.shape[0], 0 - begsam))
        pad.fill(NaN)
        dat = c_[pad, dat]

    if endsam >= n_samples:

        pad = empty((dat.shape[0], endsam - n_samples))
        pad.fill(NaN)
        dat = c_[dat, pad]

    return dat


def _read_datetime(mrk):
    for v in mrk['Marker Infos'].values():
        if v[0] == 'New Segment':
            return datetime.strptime(v[-1], '%Y%m%d%H%M%S%f')
