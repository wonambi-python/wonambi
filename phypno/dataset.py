"""Module has information about the datasets, not data.

"""

from __future__ import division
from datetime import timedelta, datetime
from glob import glob
from math import ceil
from os.path import exists, isdir, join, basename
from numpy import empty, arange, mean
from .ioeeg import Edf, Ktlx
from .datatype import DataRaw
from .utils import UnrecognizedFormat


def detect_format(filename):
    """Detect file format.

    Parameters
    ----------
    filename : str
        name of the filename or directory

    """
    if isdir(filename):
        if glob(join(filename, '*.eeg')) and glob(join(filename, '*.erd')):
            recformat = 'KTLX'
        else:
            recformat = 'unknown'
    else:

        with open(filename, 'rb') as f:
            if f.read(8) == b'0       ':
                f.seek(192)
                edf_type = f.read(5)
                if edf_type == b'EDF+C':
                    recformat = 'EDF+C'
                elif edf_type == b'EDF+D':
                    recformat = 'EDF+D'
                else:
                    recformat = 'EDF'
            else:
                recformat = 'unknown'

    return recformat


class Header:
    """Contain general information about the dataset.

    Parameters
    ----------
    filename : str
        name of the file

    Attributes
    ----------
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

    def __init__(self, filename):
        if not exists(filename):
            raise IOError('File ' + filename + 'not found')

        format_ = detect_format(filename)
        if format_ == 'EDF':
            dataset = Edf(filename)
        elif format_ == 'KTLX':
            dataset = Ktlx(filename)
        else:
            raise UnrecognizedFormat('Unrecognized format ("' + format_ + '")')

        output = dataset.return_hdr()
        self.subj_id = output[0]
        self.start_time = output[1]
        self.s_freq = output[2]
        self.chan_name = output[3]
        self.n_samples = output[4]
        self.orig = output[5]


class Dataset:
    """Contain specific information and methods, associated with a dataset.

    Parameters
    ----------
    filename : str
        name of the file

    Attributes
    ----------
    filename : str
        name of the file
    format : str
        format of the file
    header : instance of Header class

    """

    def __init__(self, filename):
        self.filename = filename
        self.format = detect_format(filename)
        try:
            self.header = Header(filename)
        except UnrecognizedFormat:
            print('could not recognized format of ' + basename(filename))

    def read_data(self, chan=None, begtime=None, endtime=None, begsam=None,
                  endsam=None, ref_chan=None):
        """Read the data and creates a DataRaw instance

        Parameters
        ----------
        chan : list of strings
            names of the channels to read
        begtime : int or datedelta or datetime
            start of the data to read;
            if it's int, it's assumed it's s;
            if it's datedelta, it's assumed from the start of the recording;
            if it's datetime, it's assumed it's absolute time
        endtime : int or datedelta or datetime
            end of the data to read;
            if it's int, it's assumed it's s;
            if it's datedelta, it's assumed from the start of the recording;
            if it's datetime, it's assumed it's absolute time
        begsample : int
            first sample to read
        endsample : int
            last sample to read

        Returns
        -------
        An instance of DataRaw

        """

        data = DataRaw()
        data.start_time = self.header.start_time
        if not isinstance(chan, list) or not all(isinstance(x, str)
                                                for x in chan):
            raise ValueError('chan should be a list of strings')
        if not chan:  # TODO: function to select channels
            chan = self.header.chan_name
        data.chan_name = chan
        idx_chan = [self.header.chan_name.index(x) for x in chan]

        if ref_chan:
            idx_ref_chan = [self.header.chan_name.index(x) for x in ref_chan]

        if begtime is not None:  # TODO: check begtime and begsample as mutually exclusive
            if isinstance(begtime, datetime):
                begtime = begtime - self.header.datetime
            if isinstance(begtime, int) or isinstance(begtime, float):
                begtime = timedelta(seconds=begtime)
            if isinstance(begtime, timedelta):
                begsam = ceil(begtime.total_seconds() * self.header.s_freq)

        if endtime is not None:  # TODO: check endtime and endsample as mutually exclusive
            if isinstance(endtime, datetime):
                endtime = endtime - self.header.start_time
            if isinstance(endtime, int) or isinstance(endtime, float):
                endtime = timedelta(seconds=endtime)
            if isinstance(endtime, timedelta):
                endsam = ceil(endtime.total_seconds() * self.header.s_freq)

        data.time = arange(begsam, endsam) / self.header.s_freq

        if self.format == 'EDF':
            dataset = Edf(self.filename)

        dat = empty(shape=(len(chan), endsam - begsam), dtype='float32')
        for i, i_chan in enumerate(idx_chan):
            dat[i, :] = dataset.return_dat(i_chan, begsam, endsam)

        if ref_chan:
            ref_dat = empty(shape=(len(ref_chan), endsam - begsam),
                            dtype='float32')
            for i, i_chan in enumerate(idx_ref_chan):
                ref_dat[i, :] = dataset.return_dat(i_chan, begsam, endsam)
            dat = dat - mean(ref_dat, 0)

        data.data = dat
        return data
