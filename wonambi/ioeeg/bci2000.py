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

STATEVECTOR = ['Name', 'Length',  'Value', 'ByteLocation', 'BitLocation']


class BCI2000:
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

    def _read_states(self):

        all_states = []
        with self.filename.open('rb') as f:
            f.seek(self.header_len, SEEK_SET)  # skip header
            StatevectorOffset = self.dtype.itemsize - self.statevector_len

            for i in range(self.n_samples):
                f.seek(StatevectorOffset, SEEK_CUR)
                raw_statevector = f.read(self.statevector_len)
                all_states.append(fromstring(raw_statevector, dtype='<u1'))

        all_states = vstack(all_states).T

        states = {}
        for statename, statedef in self.statevectors.items():
            states[statename] = array(statedef['mult'] * asmatrix(all_states[statedef['slice'], :] & statedef['mask']), dtype=int32).squeeze()

        return states


def _read_header(filename):
    """It's a pain to parse the header. It might be better to use the cpp code
    but I would need to include it here.
    """
    header = _read_header_text(filename)
    first_row = header[0]
    EXTRA_ROWS = 3  # drop DefaultValue1 LowRange1 HighRange1

    hdr = {}
    for group in finditer('(\w*)= ([\w.]*)', first_row):
        hdr[group.group(1)] = group.group(2)

    if first_row.startswith('BCI2000V'):
        VERSION = hdr['BCI2000V']

    else:
        VERSION = '1'
        hdr['DataFormat'] = 'int16'

    for row in header[1:]:
        if row.startswith('['):  # remove '[ ... Definition ]'
            section = row[2:-14].replace(' ', '')

            if section == 'StateVector':
                hdr[section] = []
            else:
                hdr[section] = {} # defaultdict(dict)
            continue

        if row == '':
            continue

        elif section == 'StateVector':
            statevector = {key: value for key, value in list(zip(STATEVECTOR, row.split(' ')))}
            hdr[section].append(statevector)

        else:
            group = match('(?P<subsection>[\w:%]*) (?P<format>\w*) (?P<key>\w*)= (?P<value>.*) // ', row)
            onerow = group.groupdict()

            values = onerow['value'].split(' ')
            if len(values) > EXTRA_ROWS:
                value = ' '.join(onerow['value'].split(' ')[:-EXTRA_ROWS])
            else:
                value = ' '.join(values)

            hdr[section][onerow['key']] = value  # similar to matlab's output

    return hdr


def _read_header_length(filename):
    with filename.open('rb') as f:
        firstchar = f.read(100)  # should be enough to read the HeaderLen
        found = search('HeaderLen= (\d*) ', firstchar.decode())
        HeaderLen = int(found.group(1))

    return HeaderLen


def _read_header_text(filename):
    HeaderLen = _read_header_length(filename)
    with filename.open('rb') as f:
        header = f.read(HeaderLen).decode().split('\r\n')

    return header


def _prepare_statevectors(sv):

    statedefs = {}

    for v in sv:
        startbyte = int(v['ByteLocation'])
        startbit  = int(v['BitLocation'])
        nbits     = int(v['Length'])
        nbytes    = (startbit + nbits) // 8
        if (startbit + nbits) % 8:
            nbytes += 1
        extrabits = int(nbytes * 8) - nbits - startbit;
        startmask = 255 & (255 << startbit)
        endmask   = 255 & (255 >> extrabits)
        div       = (1 << startbit);
        v['slice'] = slice(startbyte, startbyte + nbytes)
        v['mask'] = array([255] * nbytes, dtype=uint8)
        v['mask'][0]  &= startmask
        v['mask'][-1] &= endmask
        v['mask'].shape = (nbytes, 1)
        v['mult'] = asmatrix(256.0 ** arange(nbytes, dtype=float64) / float(div))
        statedefs[v['Name']] = v

    return statedefs
