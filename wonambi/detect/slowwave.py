"""Module to detect slow waves.

"""
from logging import getLogger
from numpy import (argmin, concatenate, diff, hstack, logical_and, newaxis, 
                   ones, percentile, roll, sign, sum, vstack, where, zeros)
from scipy.signal import firwin, kaiserord, lfilter

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QProgressDialog
except ImportError:
    pass

from .spindle import (detect_events, transform_signal, within_duration, 
                      remove_straddlers)
from ..graphoelement import SlowWaves

lg = getLogger(__name__)
MAXIMUM_DURATION = 5


class DetectSlowWave:
    """Design slow wave detection on a single channel.

    Parameters
    ----------
    method : str
        one of the predefined methods
    duration : tuple of float
        min and max duration of SWs
        
    Attributes
    ----------
    invert : bool
        pass
    trough_duration : float
        pass
    """
    def __init__(self, method='Massimini2004', duration=None):

        self.method = method
        self.trough_duration = None
        self.invert = False

        if method == 'Massimini2004':
            self.det_filt = {'order': 2,
                             'freq': (0.1, 4.)}
            self.trough_duration = (0.3, 1.)
            self.max_trough_amp = -80
            self.min_ptp = 140
            self.min_dur = 0
            self.max_dur = None

        elif method == 'AASM/Massimini2004':
            self.det_filt = {'order': 2,
                             'freq': (0.1, 4.)}
            self.trough_duration = (0.25, 1.)
            self.max_trough_amp = -40
            self.min_ptp = 75
            self.min_dur = 0
            self.max_dur = None
            
        elif method == 'Ngo2015':
            self.lowpass = {'order': 2, 
                             'freq': 3.5}
            self.min_dur = 0.833
            self.max_dur = 2.0
            self.peak_thresh = 1.25
            self.ptp_thresh = 1.25
            self.det_filt = {'freq': (0.5, 1.20)} # for repr
            
        elif method == 'Staresina2015':
            self.lowpass = {'order': 3, 
                            'freq': 1.25}
            self.min_dur = 0.8
            self.max_dur = 2.0
            self.ptp_thresh = 75
            self.det_filt = {'freq': (0.5, 1.25)} # for repr

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
        instance of graphoelement.SlowWaves
            description of the detected SWs
        """
        if parent is not None:
            progress = QProgressDialog('Finding slow waves', 'Abort', 
                                       0, data.number_of('chan')[0], parent)
            progress.setWindowModality(Qt.ApplicationModal)
            
        slowwave = SlowWaves()
        slowwave.chan_name = data.axis['chan'][0]

        all_slowwaves = []
        for i, chan in enumerate(data.axis['chan'][0]):
            
            lg.info('Detecting slow waves on chan %s', chan)
            time = hstack(data.axis['time'])
            dat_orig = hstack(data(chan=chan))
            dat_orig = dat_orig - dat_orig.mean()  # demean

            if 'Massimini2004' in self.method:
                sw_in_chan = detect_Massimini2004(dat_orig, data.s_freq, time,
                                                  self)
                
            elif 'Ngo2015' == self.method:
                sw_in_chan = detect_Ngo2015(dat_orig, data.s_freq, time, self)
                
            elif 'Staresina2015' == self.method:
                sw_in_chan = detect_Staresina2015(dat_orig, data.s_freq, time, 
                                                  self)

            else:
                raise ValueError('Unknown method')

            for sw in sw_in_chan:
                sw.update({'chan': chan})
            all_slowwaves.extend(sw_in_chan)
            
            if parent is not None:
                progress.setValue(i)
                if progress.wasCanceled():
                    return
            # end of loop over chan

        slowwave.events = sorted(all_slowwaves, key=lambda x: x['start'])

        if parent is not None:
            progress.setValue(i + 1)

        return slowwave

def detect_Massimini2004(dat_orig, s_freq, time, opts):
    """Slow wave detection based on Massimini et al., 2004.

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSlowWave'
        'det_filt' : dict
            parameters for 'butter',
        'duration' : tuple of float
            min and max duration of SW
        'min_ptp' : float
            min peak-to-peak amplitude
        'trough_duration' : tuple of float
            min and max duration of first half-wave (trough)
        'max_trough_amp' : float
            The trough amplitude has a negative value, so this parameter sets 
            the minimum depth of the trough

    Returns
    -------
    list of dict
        list of detected SWs
    float
        SW density, per 30-s epoch

    References
    ----------
    Massimini, M. et al. J Neurosci 24(31) 6862-70 (2004).

    """
    if opts.invert:
        dat_orig = -dat_orig

    dat_det = transform_signal(dat_orig, s_freq, 'double_butter', 
                               opts.det_filt)
    above_zero = detect_events(dat_det, 'above_thresh', value=0.)

    sw_in_chan = []
    if above_zero is not None:
        troughs = within_duration(above_zero, time, opts.trough_duration)
        #lg.info('troughs within duration: ' + str(troughs.shape))

        if troughs is not None:
            troughs = select_peaks(dat_det, troughs, opts.max_trough_amp)
            #lg.info('troughs deep enough: ' + str(troughs.shape))

            if troughs is not None:
                events = _add_halfwave(dat_det, troughs, s_freq, opts)
                #lg.info('SWs high enough: ' + str(events.shape))

                if len(events):
                    events = within_duration(events, time, opts.duration)
                    events = remove_straddlers(events, time, s_freq)
                    #lg.info('SWs within duration: ' + str(events.shape))

                    sw_in_chan = make_slow_waves(events, dat_det, time, s_freq)

    if len(sw_in_chan) == 0:
        lg.info('No slow wave found')

    return sw_in_chan

def detect_Ngo2015(dat_orig, s_freq, time, opts):
    """Slow wave detection based on Ngo et al., 2015.

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSlowWave'
        'lowpass' : dict
            parameters for 'low_butter',
        'duration' : tuple of float
            min and max duration of SW
        'peak_thresh' : float
            mean trough amplitude is multiplied by this scalar to yield 
            threshold; SWs above this threshold are kept
        'ptp_thresh' : float
            percentile of mean ptp values, above which SW is kept

    Returns
    -------
    list of dict
        list of detected SWs

    References
    ----------
    Ngo, H-V. et al. J Neurosci 35(17) 6630-8 (2015).

    """
    if opts.invert:
        dat_orig = -dat_orig

    sw_in_chan = []
    # filter to SO band:
    dat_det = transform_signal(dat_orig, s_freq, 'low_butter', opts.lowpass)
    # detect positive-to-negative zero crossings:
    idx_zx = find_zero_crossings(dat_det, xtype='pos_to_neg') 
    # find zero-crossing intervals within duration:
    events = find_intervals(idx_zx, s_freq, opts.duration) 
    if events is not None:
        # find start, trough, -to+ zero crossing, peak and end:
        events = find_peaks_in_slowwwave(dat_det, events)
        
        if events is not None:
            # Negative peak threshold
            idx_neg_peak = events[:, 1]
            # Trough threshhold is set as peak_thresh (float) times the mean trough amplitude over all events:
            neg_peak_thresh = dat_det[idx_neg_peak].mean() * opts.peak_thresh
            events = events[dat_det[idx_neg_peak] < neg_peak_thresh, :] 
            
            if events is not None:
                # Peak-to-peak amplitude threshold
                ptp = dat_det[events[:, 3]] - dat_det[events[:, 1]]
                # Peak-to-peak threshold is set as a percentile of the mean ptp amplitude:
                ptp_thresh = ptp.mean() * opts.ptp_thresh
                events = events[ptp > ptp_thresh, :]
                
                if events is not None:
                    events = remove_straddlers(events, time, s_freq)
                    sw_in_chan = make_slow_waves(events, dat_det, time, s_freq)
        
    if sw_in_chan:
        lg.info('No slow waves found')

    return sw_in_chan

def detect_Staresina2015(dat_orig, s_freq, time, opts):
    """Slow wave detection based on Ngo et al., 2015.

    Parameters
    ----------
    dat_orig : ndarray (dtype='float')
        vector with the data for one channel
    s_freq : float
        sampling frequency
    time : ndarray (dtype='float')
        vector with the time points for each sample
    opts : instance of 'DetectSlowWave'
        'lowpass' : dict
            parameters for 'low_butter',
        'duration' : tuple of float
            min and max duration of SW
        'ptp_thresh' : float
            percentile of mean ptp values, above which SW is kept

    Returns
    -------
    list of dict
        list of detected SWs

    References
    ----------
    Staresina, B. et al. 18(11) 1679-86 (2015).

    """
    if opts.invert:
        dat_orig = -dat_orig

    sw_in_chan = []
    
    # Create a FIR filter
    nyq_rate = s_freq / 2.0
    width = 5.0/nyq_rate
    N, beta = kaiserord(60.0, width)
    cutoff = opts.lowpass['freq']
    b = firwin(N, cutoff/nyq_rate, window=('kaiser', beta))
    
    # Filter the signal
    fir = lfilter(b, 1.0, dat_orig)
    
    # Apply the phase shift correction
    delay = int(-0.5 * (N-1))
    dat_det = roll(fir, delay)
    
    #dat_det = transform_signal(dat_orig, s_freq, 'low_butter', opts.lowpass)
    idx_zx = find_zero_crossings(dat_det, xtype='pos_to_neg') 
    events = find_intervals(idx_zx, s_freq, opts.duration)

    if events is not None:
        events = find_peaks_in_slowwwave(dat_det, events)

        if events is not None:
            # Peak-to-peak amplitude threshold
            ptp = dat_det[events[:, 3]] - dat_det[events[:, 1]]
            ptp_thresh = percentile(ptp, opts.ptp_thresh)
            events = events[ptp >= ptp_thresh, :] 
            
            if events is not None:
                events = remove_straddlers(events, time, s_freq)
                sw_in_chan = make_slow_waves(events, dat_det, time, s_freq)
        
    if sw_in_chan:
        lg.info('No slow waves found')

    return sw_in_chan

def select_peaks(data, events, limit):
    """Check whether event satisfies amplitude limit.

    Parameters
    ----------
    data : ndarray (dtype='float')
        vector with data
    events : ndarray (dtype='int')
        N x 2+ matrix with peak/trough in second position
    limit : float
        low and high limit for spindle duration

    Returns
    -------
    ndarray (dtype='int')
        N x 2+ matrix with peak/trough in second position

    """
    selected = abs(data[events[:, 1]]) >= abs(limit)

    return events[selected, :]


def make_slow_waves(events, data, time, s_freq):
    """Create dict for each slow wave, based on events of time points.

    Parameters
    ----------
    events : ndarray (dtype='int')
        N x 5 matrix with start, trough, zero, peak, end samples
    data : ndarray (dtype='float')
        vector with the data
    time : ndarray (dtype='float')
        vector with time points
    s_freq : float
        sampling frequency

    Returns
    -------
    list of dict
        list of all the SWs, with information about start,
        trough_time, zero_time, peak_time, end, duration (s), trough_val,
        peak_val, peak-to-peak amplitude (signal units), area_under_curve
        (signal units * s)
    """
    slow_waves = []
    for ev in events:
        one_sw = {'start': time[ev[0]],
                  'trough_time': time[ev[1]],
                  'zero_time': time[ev[2]],
                  'peak_time': time[ev[3]],
                  'end': time[ev[4] - 1],
                  'trough_val': data[ev[1]],
                  'peak_val': data[ev[3]],
                  'dur': (ev[4] - ev[0]) / s_freq,
                  'ptp': abs(ev[3] - ev[1])
                  }
        slow_waves.append(one_sw)

    return slow_waves


def _add_halfwave(data, events, s_freq, opts):
    """Find the next zero crossing and the intervening peak and add
    them to events. If no zero found before max_dur, event is discarded. If
    peak-to-peak is smaller than min_ptp, the event is discarded.

    Parameters
    ----------
    data : ndarray (dtype='float')
        vector with the data
    events : ndarray (dtype='int')
        N x 3 matrix with start, trough, end samples
    s_freq : float
        sampling frequency
    opts : instance of 'DetectSlowWave'
        'duration' : tuple of float
            min and max duration of SW
        'min_ptp' : float
            min peak-to-peak amplitude

    Returns
    -------
    ndarray (dtype='int')
        N x 5 matrix with start, trough, - to + zero crossing, peak, 
        and end samples
    """
    max_dur = opts.duration[1]
    if max_dur is None:
        max_dur = MAXIMUM_DURATION
    
    window = int(s_freq * max_dur)

    peak_and_end = zeros((events.shape[0], 2), dtype='int')
    events = concatenate((events, peak_and_end), axis=1)
    selected = []

    for ev in events:
        zero_crossings = where(diff(sign(data[ev[2]:ev[0] + window])))[0]
        
        if zero_crossings.any():
            ev[4] = ev[2] + zero_crossings[0] + 1
            #lg.info('0cross is at ' + str(ev[4]))
            
        else:
            selected.append(False)
            #lg.info('no 0cross, rejected')
            continue

        ev[3] = ev[2] + argmin(data[ev[2]:ev[4]])

        if abs(data[ev[1]] - data[ev[3]]) < opts.min_ptp:
            selected.append(False)
            #lg.info('ptp too low, rejected: ' + str(abs(data[ev[1]] - data[ev[3]])))
            continue

        selected.append(True)
        #lg.info('SW checks out, accepted! ptp is ' + str(abs(data[ev[1]] - data[ev[3]])))

    return events[selected, :]

def find_zero_crossings(data, xtype='all'):
    """Find indices of zero-crossings in data.
    
    Parameters
    ----------
    data : ndarray (dtype='float')
        vector with the data
    xtype : str
        if 'all', returns all zero crossings
        if 'neg_to_pos', returns only negative-to-positive zero-crossings
        if 'pos_to_neg', returns only positive-to-negative zero-crossings
        
    Returns
    -------
    nadarray of int
        indices of zero-crossings in the data
        
    Note
    ----
    A value of exactly 0 in data will always create a zero-crossing with 
    nonzero values preceding of following it.
    """
    if xtype == 'all':
        zx = where(diff(sign(data)))[0]
    elif xtype == 'neg_to_pos':
        zx = where(diff(sign(data)) > 0)[0]
    elif xtype == 'pos_to_neg':
        zx = where(diff(sign(data)) < 0)[0]
    else:
        raise ValueError(
            "Invalid xtype. Choose 'all', 'neg_to_pos' or 'pos_to_neg'.")
        
    return zx

def find_intervals(indices, s_freq, duration):
    """From sample indices, find intervals within a certain duration.
    
    Parameters
    ----------
    indices : ndarray (dtype='int')
        vector with the indices
    s_freq : float
        sampling frequency of indices/data
    duration: tuple of float
        min and max duration (s) of intervals

    Returns
    -------
    ndarray (dtype='int')
        N x 2 matrix with start and end samples
    """
    intervals = diff(indices) / s_freq
    idx_event_starts = where(logical_and(
        intervals >= duration[0],
        intervals < duration[1]
                                         ))[0]
    idx_event_ends = idx_event_starts + 1
    
    if len(idx_event_starts):
        events = vstack((indices[idx_event_starts], 
                         indices[idx_event_ends]
                         )).T
    else:
        events = None

    return events

def find_peaks_in_slowwwave(data, events):
    """Find trough, - to + zero-crossing and peak from start/end times.
    
    Parameters
    ----------
    data : ndarray (dtype='float')
        vector with the data
    events : ndarray (dtype='int')
        N x 2 matrix with start, end samples
    
    Returns
    -------
    ndarray (dtype='int')
        N x 5 matrix with start, trough, - to + zero crossing, peak, 
        and end samples
    """
    new_events = concatenate((
        events[:, 0, newaxis], 
        zeros((events.shape[0], 3), dtype='int64'), 
        events[:, 1, newaxis]), 
                        axis=1)
    
    selected = ones(events.shape[0], dtype='bool')
    for i, ev in enumerate(events):
        try:
            ev_dat = data[ev[0]:ev[1]]
            new_events[i, 1] = ev[0] + ev_dat.argmin() # trough
            new_events[i, 2] = ev[0] + where(diff(sign(ev_dat)) > 0)[0][0] # -to+
            new_events[i, 3] = ev[0] + ev_dat.argmax() # peak
        except IndexError:
            selected[i] = False
        
    return new_events[selected, :]

