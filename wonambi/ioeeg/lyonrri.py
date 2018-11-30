"""Class to import HRV RRI data in text format.
"""
from logging import getLogger
from numpy import arange, cumsum, empty, float64, interp, newaxis
from scipy.interpolate import splev, splrep
from datetime import datetime, timedelta

from .utils import DEFAULT_DATETIME

lg = getLogger(__name__)


class LyonRRI:
    """Class to read text format RR interval data from HRVanalysis export 
    (INSERM/Lyon). Returns one channel only.

    Parameters
    ----------
    rec_dir : path to record directory
        the folder containing the record
        
    Notes
    -----
    With code adapted from Rhenan Bartels: https://github.com/rhenanbartels/hrv
    """
    def __init__(self, rec_dir):
        lg.info('Reading ' + str(rec_dir))
        self.filename = rec_dir
        self.s_freq = None
        self.hdr = self.return_hdr()
        
        self.dig_min = 0
        self.dig_max = 3000
        self.phys_min = 0
        self.phys_max = 3000
        
        self.rri = self.return_rri(0, self.hdr[4])
        self.time = self.create_time(self.rri)
        self.time_interp = None
        self.rri_interp = None
        
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
        hdr['s_freq'] = self.s_freq
        hdr['chan_name'] = ['RRi']
        
        with open(self.filename, 'rt') as f:
            head = [next(f) for x in range(12)]
            hdr['subj_id'] = head[0][11:-3]
            hdr['start_time'] = DEFAULT_DATETIME
            hdr['recorder'] = head[2][10:]
            hdr['s_freq_ecg'] = int(head[3][4:]) # ECG sampling frequency
            t = datetime.strptime(head[4][16:24], '%H:%M:%S')
            hdr['total_dur'] = timedelta(hours=t.hour, minutes=t.minute, 
               seconds=t.second)
            hdr['export_date'] = DEFAULT_DATETIME
            hdr['data_type'] = head[10][11:]
            
            for i, _ in enumerate(f):
                pass
            hdr['n_samples'] = i
        
        output = (hdr['subj_id'], hdr['start_time'], hdr['s_freq'], 
                  hdr['chan_name'], hdr['n_samples'], hdr)
        
        return output
    
    def return_dat(self, chan, begsam, endsam):
        if self.rri_interp is None:
            raise ValueError('RRi has not been interpolated.')
                        
        return self.rri_interp[newaxis, begsam:endsam]

    def return_markers(self):
        """There are no markers in this format.
        """
        return []
    
    def create_time(self, rri):
        time = (cumsum(rri) / 1000.0)        
        return time - time[0]
    
    def return_rri(self, begsam, endsam):
        """Return raw, irregularly-timed RRI."""
        interval = endsam - begsam
        dat = empty(interval)
        k = 0
            
        with open(self.filename, 'rt') as f:
            [next(f) for x in range(12)]
            
            for j, datum in enumerate(f):
                
                if begsam <= j < endsam:
                    dat[k] = float64(datum[:datum.index('\t')])
                    k += 1
                    if k == interval:
                        break
                    
        return dat
    
    def interpolate(self, s_freq=4, interp_method='cubic'):
        rri = self.rri
        irregular_time = self.time
        step = 1 / float(s_freq)
        regular_time = arange(0, irregular_time[-1] + step, step)
        
        if interp_method == 'cubic':
            tck = splrep(irregular_time, rri, s=0)
            rri_interp = splev(regular_time, tck, der=0)
            
        elif interp_method == 'linear':
            rri_interp = interp(regular_time, irregular_time, rri)
            
        self.time_interp = regular_time
        self.rri_interp = rri_interp
        self.s_freq = s_freq
