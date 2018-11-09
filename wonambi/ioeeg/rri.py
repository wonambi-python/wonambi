"""Class to import HRV RRI data in text format.
"""
from logging import getLogger
from numpy import empty, float64
from datetime import datetime, timedelta
#from dateparser import parse

from .utils import DEFAULT_DATETIME

lg = getLogger(__name__)


class RRI:
    """Class to read text format RR interval data. Returns one channel only.

    Parameters
    ----------
    rec_dir : path to record directory
        the folder containing the record
        
    Notes
    -----
    Text is a very slow format for reading data. It is best to use this class
    to import the record, then to export is as an EDF, and use that for 
    reading.
    """
    def __init__(self, rec_dir):
        lg.info('Reading ' + str(rec_dir))
        self.filename = rec_dir
        self.hdr = self.return_hdr()
        
        self.dig_min = 0
        self.dig_max = 5000
        self.phys_min = 0
        self.phys_max = 5000
        
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
            the full header
        """
        hdr = {}
        hdr['chan_name'] = ['RRI']
        hdr['s_freq'] = 1
        
        with open(self.filename, 'rt') as f:
            head = [next(f) for x in range(12)]
            hdr['subj_id'] = head[0][11:-3]
            hdr['start_time'] = DEFAULT_DATETIME #parse(head[1][16:])
            hdr['recorder'] = head[2][10:]
            hdr['s_freq_time'] = int(head[3][4:])
            t = datetime.strptime(head[4][16:24], '%H:%M:%S')
            hdr['total_dur'] = timedelta(hours=t.hour, minutes=t.minute, 
               seconds=t.second)
            hdr['export_date'] = DEFAULT_DATETIME #parse(head[9][16:])
            hdr['data_type'] = head[10][11:]
            
            for i, _ in enumerate(f):
                pass
            hdr['n_samples'] = i
        
        output = (hdr['subj_id'], hdr['start_time'], hdr['s_freq'], 
                  hdr['chan_name'], hdr['n_samples'], hdr)
        
        return output
    
    def return_dat(self, chan, begsam, endsam):
        """Return the data as 2D numpy.ndarray.

        Parameters
        ----------
        chan : list of int
            index (indices) of the channels to read
        begsam : int
            index of the first sample (inclusively)
        endsam : int
            index of the last sample (exclusively)

        Returns
        -------
        numpy.ndarray
            A 2d matrix, with dimension chan X samples.
        """
        interval = endsam - begsam
        dat = empty((1, interval))
        k = 0
            
        with open(self.filename, 'rt') as f:
            [next(f) for x in range(12)]
            
            for j, datum in enumerate(f):
                
                if begsam <= j < endsam:
                    dat[0, k] = float64(datum[:datum.index('\t')])
                    k += 1
                    if k == interval:
                        break
        
        return dat

    def return_markers(self):
        """There are no markers in this format.
        """
        return []
