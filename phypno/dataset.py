"""Module has information about the datasets, not data.

"""
from datetime import timedelta, datetime
from glob import glob
from math import ceil
from logging import getLogger
from os.path import isdir, join

from numpy import arange, asarray, empty, int64

from .ioeeg import Edf, Ktlx, BlackRock, EgiMff
from .datatype import ChanTime
from .utils import UnrecognizedFormat


lg = getLogger('phypno')


def _convert_time_to_sample(abs_time, dataset):
    """Convert absolute time into samples.

    Parameters
    ----------
    abs_time : dat
        if it's int or float, it's assumed it's s;
        if it's datedelta, it's assumed from the start of the recording;
        if it's datetime, it's assumed it's absolute time.
    dataset : instance of phypno.Dataset
        dataset to get sampling frequency and start time

    Returns
    -------
    int
        sample (from the starting of the recording).

    """
    if isinstance(abs_time, datetime):
        abs_time = abs_time - dataset.header['start_time']

    if not isinstance(abs_time, timedelta):
        try:
            abs_time = timedelta(seconds=abs_time)
        except TypeError as err:
            if isinstance(abs_time, int64):
                # timedelta and int64: http://bugs.python.org/issue5476
                abs_time = timedelta(seconds=int(abs_time))
            else:
                raise err

    sample = int(ceil(abs_time.total_seconds() * dataset.header['s_freq']))
    return sample


def detect_format(filename):
    """Detect file format.

    Parameters
    ----------
    filename : str
        name of the filename or directory.

    Returns
    -------
    class used to read the data.

    """
    if isdir(filename):
        if glob(join(filename, '*.stc')) and glob(join(filename, '*.erd')):
            recformat = Ktlx
        elif (glob(join(filename, 'info.xml')) and
              glob(join(filename, 'subject.xml'))):
            recformat = EgiMff
        else:
            raise UnrecognizedFormat('Unrecognized format for directory ' +
                                     filename)
    else:

        with open(filename, 'rb') as f:
            file_header = f.read(8)
            if file_header == b'0       ':
                f.seek(192)
                edf_type = f.read(5)
                if edf_type == b'EDF+C':
                    recformat = 'EDF+C'
                elif edf_type == b'EDF+D':
                    recformat = 'EDF+D'
                else:
                    recformat = Edf
            elif file_header in (b'NEURALCD', b'NEURALSG', b'NEURALEV'):
                recformat = BlackRock
            else:
                raise UnrecognizedFormat('Unrecognized format for file ' +
                                         filename)

    return recformat


class Dataset:
    """Contain specific information and methods, associated with a dataset.

    Parameters
    ----------
    filename : str
        name of the file
    memmap : bool, optional
        whether to use memory mapping for the file

    Attributes
    ----------
    filename : str
        name of the file
    IOClass : class
        format of the file
    header : dict
        - subj_id : str
            subject identification code
        - start_time : datetime
            start time of the dataset
        - s_freq : float
            sampling frequency
        - chan_name : list of str
            list of all the channels
        - n_samples : int
            number of samples in the dataset
        - orig : dict
            additional information taken directly from the header
    dataset : instance of a class which depends on format,
        this requires at least three attributes:
          - filename
          - return_hdr
          - return_dat

    Notes
    -----
    There is a difference between Dataset.filename and Dataset.dataset.filename
    because the format is where the file that you want to read (the argument),
    while the latter is the file that you really read. There might be
    differences, for example, if the argument points to a file within a
    directory, or if the file is mapped to memory.

    """
    def __init__(self, filename, IOClass=None, memmap=False):
        self.filename = filename

        if IOClass is not None:
            self.IOClass = IOClass
        else:
            self.IOClass = detect_format(filename)

        self.dataset = self.IOClass(self.filename)
        output = self.dataset.return_hdr()
        hdr = {}
        hdr['subj_id'] = output[0]
        hdr['start_time'] = output[1]
        hdr['s_freq'] = output[2]
        hdr['chan_name'] = output[3]
        hdr['n_samples'] = output[4]
        hdr['orig'] = output[5]
        self.header = hdr

    def read_markers(self):
        """Return the markers."""
        return self.dataset.return_markers()

    def read_data(self, chan=None, begtime=None, endtime=None, begsam=None,
                  endsam=None):
        """Read the data and creates a ChanTime instance

        Parameters
        ----------
        chan : list of strings
            names of the channels to read
        begtime : int or datedelta or datetime or list
            start of the data to read;
            if it's int, it's assumed it's s;
            if it's datedelta, it's assumed from the start of the recording;
            if it's datetime, it's assumed it's absolute time.
            It can also be a list of any of the above type.
        endtime : int or datedelta or datetime
            end of the data to read;
            if it's int, it's assumed it's s;
            if it's datedelta, it's assumed from the start of the recording;
            if it's datetime, it's assumed it's absolute time.
            It can also be a list of any of the above type.
        begsam : int
            first sample to read
        endsam : int
            last sample to read

        Returns
        -------
        An instance of ChanTime

        Notes
        -----
        begsam and endsam follow Python convention, which starts at zero,
        includes begsam but DOES NOT include endsam.

        If begtime and endtime are a list, they both need the exact same
        length and the data will be stored in trials.

        """
        data = ChanTime()
        data.start_time = self.header['start_time']
        data.s_freq = self.header['s_freq']

        if chan is None:
            chan = self.header['chan_name']
        if not isinstance(chan, list):
            raise TypeError('Parameter "chan" should be a list')
        idx_chan = [self.header['chan_name'].index(x) for x in chan]

        if begtime is not None:
            if not isinstance(begtime, list):
                begtime = [begtime]
            begsam = []
            for one_begtime in begtime:
                begsam.append(_convert_time_to_sample(one_begtime, self))
        if endtime is not None:
            if not isinstance(endtime, list):
                endtime = [endtime]
            endsam = []
            for one_endtime in endtime:
                endsam.append(_convert_time_to_sample(one_endtime, self))

        if not isinstance(begsam, list):
            begsam = [begsam]
        if not isinstance(endsam, list):
            endsam = [endsam]

        if len(begsam) != len(endsam):
            raise ValueError('There should be the same number of start and ' +
                             'end point')
        n_trl = len(begsam)

        data.axis['chan'] = empty(n_trl, dtype='O')
        data.axis['time'] = empty(n_trl, dtype='O')
        data.data = empty(n_trl, dtype='O')

        for i, one_begsam, one_endsam in zip(range(n_trl), begsam, endsam):
            data.axis['chan'][i] = asarray(chan, dtype='U')
            data.axis['time'][i] = (arange(one_begsam, one_endsam) /
                                   self.header['s_freq'])

            dataset = self.dataset
            lg.debug('begsam {0: 6}, endsam {1: 6}'.format(one_begsam,
                     one_endsam))
            dat = dataset.return_dat(idx_chan, one_begsam, one_endsam)
            data.data[i] = dat

        return data
