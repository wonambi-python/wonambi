from pytest import raises

from wonambi import Dataset
from wonambi.detect.slowwave import DetectSlowWave

from .paths import psg_file

d = Dataset(psg_file)
data = d.read_data(chan=('EEG Fpz-Cz', 'EEG Pz-Oz'), begtime=27930, endtime=27960)


def test_detect_spindle_Massimini2004():
    detsw = DetectSlowWave()
    assert repr(detsw) == 'detsp_Massimini2004_0.5-02Hz_00.5-03.0s'

    sw = detsw(data)
    assert len(sw.slowwave) == 0