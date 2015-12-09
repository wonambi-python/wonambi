from logging import getLogger

from ..graphoelement import Ripple

lg = getLogger(__name__)


class DetectRipple:
    def __init__(self):
        """Design ripple detection.
        Ripples were detected as follows.
        First, data were filtered between 80–100 Hz (two-pass FIR bandpass filter, order = 3 cycles of the low frequency cut-off),
        and only artifact-free data from NREM sleep stages 2–4 were used for event detection.
        Second, the r.m.s. signal was calculated for the filtered signal using
        a moving average of 20 ms, and
        the ripple amplitude criterion was defined as the 99% percentile of
        RMS values. Third, whenever the signal exceeded this threshold
        for a minimum of 38 ms (encompassing ~3 cycles at 80 Hz) a ripple event
        was detected. In addition, we required at least three discrete peaks or
        three discrete troughs to occur in the raw signal segment corresponding
        to the above-threshold RMS segment. This was accomplished by identifying
        local maxima or minima in the respective raw signal segments after
        applying a one-pass moving average filter including the two adjacent
        data points.
        """
        pass

    def __call__(self, data):
        return Ripple()
