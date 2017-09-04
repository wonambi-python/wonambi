"""Module to detect slow waves.

"""
from logging import getLogger
from numpy import (absolute, arange, argmax, asarray, concatenate, cos, diff,
                   exp, empty, floor, hstack, insert, int8, invert, linspace,
                   mean, median, nan, ones, pi, ptp, sqrt, square, std, vstack,
                   where, zeros)
from scipy.ndimage.filters import gaussian_filter
from scipy.signal import (argrelmax, butter, cheby2, filtfilt, fftconvolve,
                          hilbert, periodogram)

from ..graphoelement import SlowWave

lg = getLogger(__name__)


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
    def __init__(self, method='Massimini2004', frequency=None, duration=None):

        if frequency is None:
            frequency = (0.5, 2)
        if duration is None:
            duration = (0.5, 3)

        self.method = method
        self.frequency = frequency
        self.duration = duration

        if method == 'Massimini2004':
            pass

        else:
            raise ValueError('Unknown method')

    def __repr__(self):
        return ('detsp_{0}_{1:02}-{2:02}Hz_{3:04.1f}-{4:04.1f}s'
                ''.format(self.method, self.frequency[0], self.frequency[1],
                          self.duration[0], self.duration[1]))

    def __call__(self, data, make_plots=False):
        """Detect slow waves on the data.

        Parameters
        ----------
        data : instance of Data
            data used for detection

        Returns
        -------
        instance of graphoelement.SlowWaves
            description of the detected SWs
        """
        slowwave = SlowWave()
        slowwave.chan_name = data.axis['chan'][0]
        slowwave.det_value = zeros(data.number_of('chan')[0])
        slowwave.sel_value = zeros(data.number_of('chan')[0])
        slowwave.density = zeros(data.number_of('chan')[0])

        all_slowwaves = []
        for i, chan in enumerate(data.axis['chan'][0]):
            lg.info('Detecting slow waves on chan %s', chan)
            time = hstack(data.axis['time'])
            dat_orig = hstack(data(chan=chan))

            if self.method == 'Massimini2004':
                sw_in_chan, values, density = detect_Massimini2004(dat_orig,
                                                                   data.s_freq,
                                                                   time, self)

            else:
                raise ValueError('Unknown method')

            slowwave.det_value[i] = values['det_value']
            slowwave.sel_value[i] = values['sel_value']
            slowwave.density[i] = density
            for sw in sw_in_chan:
                sw.update({'chan': chan})
            all_slowwaves.extend(sw_in_chan)
            # end of loop over chan

        slowwave.slowwave = sorted(all_slowwaves,
                                   key=lambda x: x['start_time'])

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
        'duration' : tuple of float
            min and max duration of SWs

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
    # dat_det = transform_signal(dat_orig, s_freq, 'butter', opts.det_butter)
    # below_zero = detect_runs(dat_det, lambda x: x < 0)
    return [], {'det_value': None, 'sel_value': None}, 0


def detect_runs(data, function):
    is_true = concatenate(([0], function(data).view(int8), [0]))
    absdiff = abs(diff(is_true))
    ranges = where(absdiff == 1)[0].reshape(-1, 2)

    return ranges
