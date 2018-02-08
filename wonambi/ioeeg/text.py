"""Class to import straight text records.
"""
from logging import getLogger
from numpy import empty, float64, floor
from os import listdir
from os.path import splitext
from pathlib import Path

from .utils import DEFAULT_DATETIME

lg = getLogger(__name__)


class Text:
    """Class to read text format records. The record consists of a directory 
    containing txt files. Each file is a  channel. The first line of each file 
    is the sampling rate, and the following lines are single data points, 
    in scientific notation.
    Only supports a single sampling rate for all channels.

    Parameters
    ----------
    rec_dir : path to record directory
        the folder containing the record
        
    Notes
    -----
    Text is a very slow format for reading data. It is best to use this class
    to import the record, then to export is as a Wonambi (.won) file, and use
    that for reading.
    """
    def __init__(self, rec_dir):
        lg.info('Reading ' + str(rec_dir))
        self.filename = rec_dir
        self.hdr = self.return_hdr()
        
        # range data are absent
        self.dig_min = -0.000512 # estimated from min values
        self.dig_max = 0.000512 # estimated from max values
        self.phys_min = -800 # estimate
        self.phys_max = 800 # estimate
        
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
        foldername = Path(self.filename)
        chan_files = self.chan_files = []
        hdr = {}
        hdr['chan_name'] = []
        hdr['start_time'] = DEFAULT_DATETIME
        
        for file in listdir(self.filename):
            base, suffix = splitext(file)
            if suffix == '.txt':
                if base[-3:] == 'hyp':
                    self.hypno_file = file
                else:
                    chan_files.append(foldername / file)
                    chan_name = base[base.index('_') + 1:]
                    hdr['chan_name'].append(chan_name)
                    hdr['subj_id'] = base[:base.index('_')]
                    
        if not chan_files:
            raise FileNotFoundError('No channel found.')
            return
        
        with open(chan_files[0], 'rt') as f:
            line0 = f.readline()
            hdr['s_freq'] = int(
                    line0[line0.index('Rate:') + 5:line0.index('Hz')])
            
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
        #n_sam = self.hdr[4]
        interval = endsam - begsam
        dat = empty((len(chan), interval))
        
        #beg_block = floor((begsam / n_sam) * n_block)
        #end_block = floor((endsam / n_sam) * n_block)
                
        for i, chan in enumerate(chan):
            k = 0
            
            with open(self.chan_files[chan], 'rt') as f:
                f.readline()
                
                for j, datum in enumerate(f):
                    
                    if begsam <= j + 1 < endsam:
                        dat[i, k] = float64(datum)
                        k += 1
                        if k == interval:
                            break
        
        # calibration
        phys_range = self.phys_max - self.phys_min
        dig_range = self.dig_max - self.dig_min
        gain = phys_range / dig_range
        dat *= gain
        
        return dat

    def return_markers(self):
        """There are no markers in this format.
        """
        return []

    
#==============================================================================
# def split_file(filepath, lines_per_file=100):
#     """splits file at `filepath` into sub-files of length `lines_per_file`
#     """
#     lpf = lines_per_file
#     path, filename = split(filepath)
#     with open(filepath, 'r') as r:
#         name, ext = splitext(filename)
#         try:
#             w = open(join(path, '{}_{}{}'.format(name, 0, ext)), 'w')
#             for i, line in enumerate(r):
#                 if not i % lpf:
#                     #possible enhancement: don't check modulo lpf on each pass
#                     #keep a counter variable, and reset on each checkpoint lpf.
#                     w.close()
#                     filename = join(path,
#                                     name,
#                                     '{}{}'.format(i, ext))
#                     w = open(filename, 'w')
#                 w.write(line)
#         finally:
#             w.close()
#==============================================================================
