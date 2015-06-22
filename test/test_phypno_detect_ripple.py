from phypno.graphoelement import Ripple
from phypno.detect import DetectRipple


def test_ripple_01():
    det_rp = DetectRipple()
    rp = det_rp(None)
    assert isinstance(rp, Ripple)
