"""Module to detect slow waves.

"""
from logging import getLogger
from numpy import argmax, concatenate, diff, hstack, sign, sum, where, zeros

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
    frequency : tuple of float
        low and high frequency of SW band
    duration : tuple of float
        min and max duration of SWs
    """
    def __init__(self, method='Massimini2004', duration=None):

        self.method = method

        if method == 'Massimini2004':
            self.det_filt = {'order': 3,
                             'freq': (0.1, 4.)}
            self.trough_duration = (0.3, 1.)
            self.max_trough_amp = - 80
            self.min_ptp = 140
            self.min_dur = 0
            self.max_dur = None
            self.invert = False

        elif method == 'AASM/Massimini2004':
            self.det_filt = {'order': 3,
                             'freq': (0.1, 4.)}
            self.trough_duration = (0.25, 1.)
            self.max_trough_amp = - 40
            self.min_ptp = 75
            self.min_dur = 0
            self.max_dur = None
            self.invert = False

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
            progress = QProgressDialog('Finding spindles', 'Abort', 
                                       0, data.number_of('chan')[0], parent)
            progress.setWindowModality(Qt.ApplicationModal)
            
        slowwave = SlowWaves()
        slowwave.chan_name = data.axis['chan'][0]

        all_slowwaves = []
        for i, chan in enumerate(data.axis['chan'][0]):
            
            if parent is not None:
                progress.setValue(i)
            
            lg.info('Detecting slow waves on chan %s', chan)
            time = hstack(data.axis['time'])
            dat_orig = hstack(data(chan=chan))

            if 'Massimini2004' in self.method:
                sw_in_chan = detect_Massimini2004(dat_orig, data.s_freq, time,
                                                  self)

            else:
                raise ValueError('Unknown method')

            for sw in sw_in_chan:
                sw.update({'chan': chan})
            all_slowwaves.extend(sw_in_chan)
            # end of loop over chan

        lg.info('number of SW: ' + str(len(all_slowwaves)))
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
    below_zero = detect_events(dat_det, 'below_thresh', value=0.)

    sw_in_chan = []
    if below_zero is not None:
        troughs = within_duration(below_zero, time, opts.trough_duration)
        #lg.info('troughs within duration: ' + str(troughs.shape))

        if troughs is not None:
            troughs = select_peaks(dat_det, troughs, opts.max_trough_amp)
            #lg.info('troughs deep enough: ' + str(troughs.shape))

            if troughs is not None:
                events = _add_pos_halfwave(dat_det, troughs, s_freq, opts)
                #lg.info('SWs high enough: ' + str(events.shape))

                if len(events):
                    events = within_duration(events, time, opts.duration)
                    events = remove_straddlers(events, time, s_freq)
                    #lg.info('SWs within duration: ' + str(events.shape))

                    sw_in_chan = make_slow_waves(events, dat_det, time, s_freq)

    if len(sw_in_chan) == 0:
        lg.info('No slow wave found')

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
                  'area_under_curve': sum(data[ev[0]: ev[4]]) / s_freq,
                  'ptp': abs(ev[3] - ev[1])
                  }
        slow_waves.append(one_sw)

    return slow_waves


def _add_pos_halfwave(data, events, s_freq, opts):
    """Find the next zero crossing and the intervening positive peak and add
    them to events. If no zero found before max_dur, event is discarded. If
    peak-to-peak is smaller than min_ptp, the event is discarded.

    Parameters
    ----------
    data : ndarray (dtype='float')
        vector with the data
    events : ndarray (dtype='int')
        N x 3 matrix with start, peak, end samples
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
        N x 5 matrix with start, trough, - to + zero crossing, peak, and end
        samples
    """
    max_dur = opts.duration[1]
    if max_dur is None:
        max_dur = MAXIMUM_DURATION
    
    window = int(s_freq * max_dur)
    lg.info('window: ' + str(window))

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

        ev[3] = ev[2] + argmax(data[ev[2]:ev[4]])

        if abs(data[ev[1]] - data[ev[3]]) < opts.min_ptp:
            selected.append(False)
            #lg.info('ptp too low, rejected: ' + str(abs(data[ev[1]] - data[ev[3]])))
            continue

        selected.append(True)
        #lg.info('SW checks out, accepted! ptp is ' + str(abs(data[ev[1]] - data[ev[3]])))

    return events[selected, :]
