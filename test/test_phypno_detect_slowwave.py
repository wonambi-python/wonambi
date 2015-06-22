from phypno.graphoelement import SlowWave
from phypno.detect import DetectSlowWave

def test_slowwave_01():
    det_sw = DetectSlowWave()
    sw = det_sw(None)
    assert isinstance(sw, SlowWave)
