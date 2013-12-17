from ..graphoelement import Ripple


class DetectRipple:
    def __init__(self):
        """Design ripple detection.

        1. Axmacher, N., Elger, C. E. & Fell, J. Brain 131, 1806–17 (2008).
        Data from -250ms to +250ms around these events were excluded. Ripples
        were detected by filtering the data between 80Hz and 140Hz (Butterworth
        filter, 48 dB/octave) and then selecting all events, which exceeded an
        amplitude of 20 mVin 12.5ms time windows contiguously lasting for at
        least 25ms length.

        """
        pass

    def __call__(self, data):
        return Ripple()
