from wonambi import Dataset
from wonambi.detect.slowwave import DetectSlowWave

from .paths import psg_file

d = Dataset(psg_file)
data = d.read_data(chan=('EEG Fpz-Cz', 'EEG Pz-Oz'), begtime=27930, endtime=27960)


def test_detect_spindle_Massimini2004():
    detsw = DetectSlowWave()
    assert repr(detsw) == 'detsw_Massimini2004_0.10-4.00Hz_0.50-3.00s'

    sw = detsw(data)
    assert len(sw.events) == 0


def test_detect_spindle_AASM_Massimini2004():
    detsw = DetectSlowWave(method='AASM/Massimini2004')
    assert repr(detsw) == 'detsw_AASM/Massimini2004_0.10-4.00Hz_0.50-3.00s'

    sw = detsw(data)
    assert len(sw.events) == 0
