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
    format : str
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
    def __init__(self, filename, memmap=False):
        self.filename = filename
        self.format = detect_format(filename)

        if self.format == 'EDF':
            self.dataset = Edf(filename)
        elif self.format == 'KTLX':
            self.dataset = Ktlx(filename)
        else:
            raise UnrecognizedFormat('Unrecognized format ("' + self.format +
                                     '")')

        output = self.dataset.return_hdr()
        hdr = {}
        hdr['subj_id'] = output[0]
        hdr['start_time'] = output[1]
        hdr['s_freq'] = output[2]
        hdr['chan_name'] = output[3]
        hdr['n_samples'] = output[4]
        hdr['orig'] = output[5]
        self.header = hdr

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
        begsam : int
            first sample to read
        endsam : int
            last sample to read

        Returns
        -------
        An instance of DataRaw

        Notes
        -----
        begsam and endsam follow Python convention, which starts at zero,
        includes begsam but DOES NOT include endsam.

        """

        data = DataRaw()
        data.start_time = self.header['start_time']
        if not chan:
            chan = self.header['chan_name']
        if not isinstance(chan, list) or not all(isinstance(x, str)
                                                 for x in chan):
            raise ValueError('chan should be a list of strings')
        data.chan_name = chan
        idx_chan = [self.header['chan_name'].index(x) for x in chan]

        if ref_chan:
            idx_ref_chan = [self.header['chan_name'].index(x)
                            for x in ref_chan]

        if begtime is not None:  # TODO: check begtime and begsample as mutually exclusive
            if isinstance(begtime, datetime):
                begtime = begtime - self.header['datetime']
            if isinstance(begtime, int) or isinstance(begtime, float):
                begtime = timedelta(seconds=begtime)
            if isinstance(begtime, timedelta):
                begsam = ceil(begtime.total_seconds() * self.header.s_freq)

        if endtime is not None:  # TODO: check endtime and endsample as mutually exclusive
            if isinstance(endtime, datetime):
                endtime = endtime - self.header['datetime']
            if isinstance(endtime, int) or isinstance(endtime, float):
                endtime = timedelta(seconds=endtime)
            if isinstance(endtime, timedelta):
                endsam = ceil(endtime.total_seconds() * self.header.s_freq)

        data.time = arange(begsam, endsam) / self.header['s_freq']

        dataset = self.dataset
        dat = empty(shape=(len(chan), endsam - begsam), dtype='float32')

        # TODO: should pass all the channels at the same time
        for i, i_chan in enumerate(idx_chan):
            dat[i, :] = dataset.return_dat(i_chan, begsam, endsam)

        # TODO: should pass all the channels at the same time
        if ref_chan:
            ref_dat = empty(shape=(len(ref_chan), endsam - begsam),
                            dtype='float32')
            for i, i_chan in enumerate(idx_ref_chan):
                ref_dat[i, :] = dataset.return_dat(i_chan, begsam, endsam)
            dat = dat - mean(ref_dat, 0)

        data.data = dat
        return data
