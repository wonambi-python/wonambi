from os.path import getsize, join
from xml.etree.ElementTree import parse
from datetime import datetime, timedelta

from numpy import reshape, zeros

from ..utils.timezone import utc

# note that the time is in "local" Unix Time, which is in the local time zone,
# so we read it as "UTC" (meaning, do not apply timezone transformation) and
# then remove timezone info.
TIMEZONE = utc
# 24bit precision
DATA_PRECISION = 3

EEG_FILE = 'EEG,Composite,SampleSeries,Composite,MRIAmp,data'
SETTINGS_FILE = 'EEG,Composite,SampleSeries,Composite,MRIAmp,settings'


class Moberg:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory
    """
    def __init__(self, filename):
        self.filename = filename
        self.n_chan = None

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
        subj_id = str()
        patient = parse(join(self.filename, 'patient.info'))
        for patientname in ['PatientFirstName', 'PatientLastName']:
            subj_id += patient.findall(patientname)[0].text.strip()

        unix_time = int(patient.findall('TimeStamp')[0].text.strip()) / 1e6
        system_offset = int(patient.findall('SystemOffset')[0].text.strip())
        print(system_offset)
        start_time = (datetime.fromtimestamp(unix_time, TIMEZONE) +
                      timedelta(seconds=system_offset)).replace(tzinfo=None)

        s_freq = 256  # could not find it in the text files

        montage = parse(join(self.filename, 'Montage.xml'))
        chan_str = montage.findall('MontageChannels')[0].text.strip()
        chan_list = chan_str.split(',')
        chan_name = [x.replace(';', ' - ') for x in chan_list]

        data_size = getsize(join(self.filename, EEG_FILE))
        n_samples = int(data_size / DATA_PRECISION / len(chan_name))

        self.n_chan = len(chan_name)
        settings = parse(join(self.filename, SETTINGS_FILE))
        conversion = settings.findall('SampleConversion')[0].text.strip()

        dig_min, dig_max, anl_min, anl_max = [int(x) for x in
                                              conversion.split(',')]

        if dig_max == -dig_min and anl_max == -anl_min:
            self.convertion = lambda dat: dat / dig_max * anl_max
        else:
            self.convertion = lambda dat: ((dat + dig_min) /
                                           (dig_max - dig_min) *
                                           (anl_max - anl_min) + anl_min)

        orig = {'patient': patient,
                'montage': montage,
                'settings': settings,
                }

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
        first_sam = DATA_PRECISION * self.n_chan * begsam
        toread_sam = DATA_PRECISION * self.n_chan * (endsam - begsam)

        with open(join(self.filename, EEG_FILE), 'rb') as f:
            f.seek(first_sam)
            x = f.read(toread_sam)

        dat = _read_dat(x)
        dat = reshape(dat, (self.n_chan, -1), 'F')

        return self.convertion(dat[chan, :])

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


def _read_dat(x):
    """read 24bit binary data and convert them to numpy.

    Parameters
    ----------
    x : bytes
        bytes (length should be divisible by 3)

    Returns
    -------
    numpy vector
        vector with the signed 24bit values

    Notes
    -----
    It's pretty slow but it's pretty a PITA to read 24bit as far as I can tell.
    """
    n_smp = int(len(x) / DATA_PRECISION)
    dat = zeros(n_smp)

    for i in range(n_smp):
        i0 = i * DATA_PRECISION
        i1 = i0 + DATA_PRECISION
        dat[i] = int.from_bytes(x[i0:i1], byteorder='little', signed=True)

    return dat
