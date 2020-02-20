"""Class to import HRV RRI data in text format.
"""
from logging import getLogger
from os.path import basename, splitext
from numpy import (arange, cumsum, empty, float64, interp, isnan, nan, newaxis, 
                   where)
from scipy.interpolate import splev, splrep
from datetime import datetime, timedelta
from dateutil.parser import parse
from pandas import read_excel

lg = getLogger(__name__)


class MindWareIBI:
    """Class to read interbeat intervals (IBI) from Excel workbook exported 
    from MindWare. Returns one channel only.

    Parameters
    ----------
    rec_dir : path to record directory
        the folder containing the record
    """
    def __init__(self, rec_dir):
        lg.info('Reading ' + str(rec_dir))
        self.filename = rec_dir
        self.s_freq = None
        
        self.dig_min = 0
        self.dig_max = 3000
        self.phys_min = 0
        self.phys_max = 3000
        
        self.ibi = self.return_ibi()
        self.time = self.create_time(self.ibi)
        self.interpolate()        
        self.hdr = self.return_hdr()
        
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
        hdr['chan_name'] = ['IBI']
        
        d = read_excel(self.filename, sheet_name='HRV Stats', 
                       parse_dates=False).to_numpy(dtype=str)
        hdr['subj_id'] = splitext(basename(d[2, 1]))[0]
        hdr['start_time'] = parse(' '.join((d[0, 1], d[1, 1])))
        hdr['s_freq_ecg'] = int(d[25, 1]) # ECG sampling frequency
        hdr['n_samples'] = len(self.ibi_interp)
        
        output = (hdr['subj_id'], hdr['start_time'], hdr['s_freq'], 
                  hdr['chan_name'], hdr['n_samples'], hdr)
        
        return output
    
    def return_dat(self, chan, begsam, endsam):
        if self.ibi_interp is None:
            raise ValueError('IBI has not been interpolated.')
                        
        return self.ibi_interp[newaxis, begsam:endsam]

    def return_markers(self):
        """There are no markers in this format.
        """
        return []
    
    def create_time(self, ibi):
        time = cumsum(ibi) / 1000.0        
        return time - time[0]
    
    def return_ibi(self, begsam=None, endsam=None):
        """Return raw, irregularly-timed IBI."""
        dat = read_excel(self.filename, sheet_name='IBI Series').to_numpy()
        
        for i in range(dat.shape[1] - 1):
            try:
                idx_last_val = where(isnan(dat[:, i]))[0][0] - 1
            except IndexError:
                idx_last_val = dat.shape[0] - 1
            dat[0, i + 1] = dat[0, i + 1] + dat[idx_last_val, i]
            dat[idx_last_val, i] = nan
        
        dat_1d = dat.T.ravel()
        ibi = dat_1d[~isnan(dat_1d)][:-1]
        
        return ibi[begsam:endsam]
    
    def interpolate(self, s_freq=4, interp_method='cubic'):
        ibi = self.ibi.copy()
        irregular_time = self.time
        step = 1 / float(s_freq)
        regular_time = arange(0, irregular_time[-1] + step, step)
        
        if interp_method == 'cubic':
            tck = splrep(irregular_time, ibi, s=0)
            ibi_interp = splev(regular_time, tck, der=0)
            
        elif interp_method == 'linear':
            ibi_interp = interp(regular_time, irregular_time, ibi)
            
        self.time_interp = regular_time
        self.ibi_interp = ibi_interp
        self.s_freq = s_freq
