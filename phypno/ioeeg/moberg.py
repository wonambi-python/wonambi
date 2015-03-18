from os.path import getsize, join
from xml.etree.ElementTree import parse
from datetime import datetime

from ..utils.timezone import Eastern

# we assume that it was recorded in EST
# but maybe local could be good too.
TIMEZONE = Eastern
# 24bit precision
DATA_PRECISION = 3

EEG_FILE = 'EEG,Composite,SampleSeries,Composite,MRIAmp,data'


class Moberg:
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
        subj_id = str()
        patient = parse(join(self.filename, 'patient.info'))
        for patientname in ['PatientFirstName', 'PatientLastName']:
            subj_id += patient.findall(patientname)[0].text.strip()

        unix_time = int(patient.findall('TimeStamp')[0].text.strip()) / 1e6
        start_time = datetime.fromtimestamp(unix_time, TIMEZONE)

        s_freq = 256  # could not find it in the text files

        montage = parse(join(self.filename, 'Montage.xml'))
        chan_str = montage.findall('MontageChannels')[0].text.strip()
        chan_list = chan_str.split(',')
        chan_name = [x.replace(';', ' - ') for x in chan_list]

        data_size = getsize(join(self.filename, EEG_FILE))
        n_samples = int(data_size / DATA_PRECISION / len(chan_name) / s_freq)
        orig = {'patient': patient,
                'montage': montage,
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
        data = rand(10, 100)
        return data[chan, begsam:endsam]

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
        markers = [{'name': 'one_trigger',
                    'start': 10,
                    'end': 15,  # duration of 5s
                    'chan': ['chan1', 'chan2'],  # or None
                    }]
        return markers
