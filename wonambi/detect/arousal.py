"""Module to detect arousals
"""

from logging import getLogger
from numpy import abs, argmin, asarray, hstack, mean, sum, vstack, where, zeros
from scipy.signal import spectrogram

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QProgressDialog
except ImportError:
    pass

from .spindle import within_duration, remove_straddlers
from ..graphoelement import Arousals

lg = getLogger(__name__)


class DetectArousal:
    """Design slow wave detection on a single channel.

    Parameters
    ----------
    method : str
        one of the predefined methods
    freq_band : tuple of (float or None)
        frequency band of interest in Hz
    spectrogram : dict
        'dur': float
            window length in sec 
        'overlap': float
            ratio of overlap between consecutive windows 
        'detrend': str
            'constant', 'linear' or False
    det_thresh : float
        minimum factor increase of mean frequency between consecutive windows
    min_interval : float
        minimum duration between consecutive arousals, in sec
    duration : tuple of float
        min and max duration of arousals
    """
    def __init__(self, method='HouseDetector', duration=None):

        self.method = method

        if method == 'HouseDetector':
            self.freq_band1 = (5, None)
            self.freq_band2 = (0.2, None)
            self.spectrogram = {'dur': 1,
                                'overlap': 0.5,
                                'detrend': 'linear'}
            self.det_thresh = 1.2
            self.det_thresh_end = 1.1
            self.min_interval = 10
            self.duration = (3, 30)

        else:
            raise ValueError('Unknown method')
            
        if duration is None:
            self.duration = (self.min_dur, self.max_dur)       
        else:
            self.duration = duration

    def __repr__(self):
        return ('detsw_{0}_{1:04.2f}-{2:04.2f}Hz'
                ''.format(self.method, *self.det_filt['freq']))

    def __call__(self, data, parent=None):
        """Detect slow waves on the data.

        Parameters
        ----------
        data : instance of Data
            data used for detection
        parent : QWidget
            for use with GUI, as parent widget for the progress bar
        
        Returns
        -------
        instance of graphoelement.Arousals
            description of the detected arousals
        """
        if parent is not None:
            progress = QProgressDialog('Finding arousals', 'Abort', 
                                       0, data.number_of('chan')[0], parent)
            progress.setWindowModality(Qt.ApplicationModal)
            
        arousal = Arousals()
        arousal.chan_name = data.axis['chan'][0]

        all_arousals = []
        for i, chan in enumerate(data.axis['chan'][0]):
            
            lg.info('Detecting arousals on chan %s', chan)
            time = hstack(data.axis['time'])
            dat_orig = hstack(data(chan=chan))

            if 'HouseDetector' in self.method:
                arou_in_chan = detect_HouseDetector(dat_orig, data.s_freq, time,
                                                  self)

            else:
                raise ValueError('Unknown method')

            for ar in arou_in_chan:
                ar.update({'chan': chan})
            all_arousals.extend(arou_in_chan)
            
            if parent is not None:
                progress.setValue(i)
                if progress.wasCanceled():
                    return
            # end of loop over chan

        arousal.events = sorted(all_arousals, key=lambda x: x['start'])

        if parent is not None:
            progress.setValue(i + 1)

        return arousal

def detect_HouseDetector(dat_orig, s_freq, time, opts):
    """House arousal detection.

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSlowWave'
        'duration' : tuple of float
            min and max duration of arousal

    Returns
    -------
    list of dict
        list of detected arousals
    float
        arousal density, per 30-s epoch
    """  
    nperseg = int(opts.spectrogram['dur'] * s_freq)
    overlap = opts.spectrogram['overlap']
    noverlap = int(overlap * nperseg)
    detrend = opts.spectrogram['detrend']
    min_interval = int(opts.min_interval * s_freq)
    
    sf, t, dat_det = spectrogram(dat_orig, 
                                 fs=s_freq, 
                                 nperseg=nperseg, 
                                 noverlap=noverlap, 
                                 detrend=detrend)
    freq1 = opts.freq_band1
    freq2 = opts.freq_band2
    f0 = asarray([abs(freq1[0] - x) for x in sf]).argmin() if freq1[0] else None
    f1 = asarray([abs(freq1[1] - x) for x in sf]).argmin() if freq1[1] else None
    f2 = asarray([abs(freq2[1] - x) for x in sf]).argmin() if freq2[1] else None
    f3 = asarray([abs(freq2[1] - x) for x in sf]).argmin() if freq2[1] else None
    
    dat_eq1 = zeros(dat_det.shape[1])
    dat_eq2 = zeros(dat_det.shape[1])
    for i in range(dat_det.shape[1]):
        dat_eq1[i] = splitpoint(dat_det[f0:f1, i], sf[f0:f1])
        dat_eq2[i] = splitpoint(dat_det[f2:f3, i], sf[f2:f3])
        
    dat_acc = dat_eq1[1:] / dat_eq1[:-1]
    starts = dat_acc >= opts.det_thresh
    print(f'starts: {sum(starts)}')
    print(f'1.01: {sum(dat_acc >= 1.01)}')
    print(f'1.02: {sum(dat_acc >= 1.02)}')
    print(f'1.05: {sum(dat_acc >= 1.05)}')
    print(f'1.1: {sum(dat_acc >= 1.1)}')
    print(f'1.2: {sum(dat_acc >= 1.2)}')
    print(f'1.3: {sum(dat_acc >= 1.3)}')
    print(f'1.4: {sum(dat_acc >= 1.4)}')
    print(f'1.5: {sum(dat_acc >= 1.5)}')
    print(f'1.75: {sum(dat_acc >= 1.75)}')
    print(f'2: {sum(dat_acc >= 2)}')
    print(f'2.5: {sum(dat_acc >= 2.5)}')
    print(f'3: {sum(dat_acc >= 3)}')
    print(f'5: {sum(dat_acc >= 5)}')
    print(f'10: {sum(dat_acc >= 10)}')
    
    if starts.any():
        new_starts = asarray(zeros(len(starts)), dtype=bool)
        ends = asarray(zeros(len(starts) - 1), dtype=bool)
        iter_len = len(starts) - 2
        i = 0
        while i <= iter_len:
            if starts[i]:
                for j, k in enumerate(dat_eq2[i + 2:-1]):
                    if k < dat_eq2[i] * opts.det_thresh_end:
                        new_starts[i] = True
                        ends[i + j + 1] = True
                        break
                i += j + min_interval
            else:
                i += 1
        
        if sum(new_starts) > sum(ends): # a start without an end
            ends[-1] = True
        
        events = vstack((where(new_starts == True)[0] + 1,
                         where(ends == True)[0] + 2)).T
        if overlap: 
            events = events - int(1 / 2 / overlap) # from win centre to win start
        events = events * (nperseg - noverlap) # upsample
        print(f'n_events before dur = {events.shape}')
        events = within_duration(events, time, opts.duration)
        print(f'n_events after dur = {events.shape}')
        events = remove_straddlers(events, time, s_freq)
        print(f'n_events after strad = {events.shape}')
    
        ar_in_chan = make_arousals(events, time, s_freq)
        
    else:
        lg.info('No arousals found')
        ar_in_chan = []

    return ar_in_chan


def splitpoint(a, sf):
    c1 = a.cumsum()
    c2 = a[::-1].cumsum()[::-1]
    split = argmin(abs(c1-c2))
    return sf[split]

def make_arousals(events, time, s_freq):
    """Create dict for each arousal, based on events of time points.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 5 matrix with start, end samples
    data : ndarray (dtype='float')
        vector with the data
    time : ndarray (dtype='float')
        vector with time points
    s_freq : float
        sampling frequency

    Returns
    -------
    list of dict
        list of all the arousals, with information about start, end, 
        duration (s),
    """
    arousals = []
    for ev in events:
        one_ar = {'start': time[ev[0]],
                  'end': time[ev[1] - 1],
                  'dur': (ev[1] - ev[0]) / s_freq,
                  }
        arousals.append(one_ar)

    return arousals
