from os import SEEK_SET, SEEK_END
from re import search, finditer, match
from datetime import datetime

from numpy import fromfile, dtype

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
        """
        orig = {}
        orig = _read_header(self.filename)

        nchan = int(orig['SourceCh'])
        chan_name = ['ch{:03d}'.format(i) for i in range(nchan)]
        chan_dtype = dtype(orig['DataFormat'])
        StatevectorLen = int(orig['StatevectorLen'])

        s_freq = int(orig['Parameter']['SamplingRate'])
        storagetime = orig['Parameter']['StorageTime'].replace('%20', ' ')
        try:  # newer version
            start_time = datetime.strptime(storagetime, '%a %b %d %H:%M:%S %Y')
        except:
            start_time = datetime.strptime(storagetime, '%Y-%m-%dT%H:%M:%S')

        subj_id = orig['Parameter']['SubjectName']

        self.dtype = dtype([(chan, chan_dtype) for chan in chan_name]
                            + [('statevector', 'S', StatevectorLen)])

        # compute n_samples based on file size - header
        with open(self.filename, 'rb') as f:
            f.seek(0, SEEK_END)
            EOData = f.tell()
        n_samples = (EOData - int(orig['HeaderLen'])) / self.dtype.itemsize

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

        BEGSAMPLE = 0

        with self.filename.open('rb') as f:
            f.seek(14627, SEEK_SET)  # skip header

            f.seek(DTYPE.itemsize * BEGSAMPLE, SEEK_CUR)
            dat = fromfile(f, dtype=DTYPE, count=100)

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
