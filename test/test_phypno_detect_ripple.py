from . import *

from phypno.graphoelement import Ripple
from phypno.detect import DetectRipple


def test_ripple_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    det_rp = DetectRipple()
    rp = det_rp(None)
    assert isinstance(rp, Ripple)
