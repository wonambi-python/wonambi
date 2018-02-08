from pytest import approx

from wonambi import Dataset
from wonambi.detect.slowwave import DetectSlowWave

from .paths import psg_file

d = Dataset(psg_file)
data = d.read_data(chan=('EEG Fpz-Cz', 'EEG Pz-Oz'), begtime=27930, endtime=27960)


def test_detect_slowwave_Massimini2004():
    detsw = DetectSlowWave()
    assert repr(detsw) == 'detsw_Massimini2004_0.10-4.00Hz'

    sw = detsw(data)
    assert len(sw.events) == 2


def test_detect_slowwave_AASM_Massimini2004():
    detsw = DetectSlowWave(method='AASM/Massimini2004')
    assert repr(detsw) == 'detsw_AASM/Massimini2004_0.10-4.00Hz'

    sw = detsw(data)
    assert len(sw.events) == 14


def test_detect_slowwave_to_data():
    detsw = DetectSlowWave()
    sw = detsw(data)

    sw_data = sw.to_data('count')
    assert sw_data(0)[1] == 2

    sw_auc = sw.to_data('area_under_curve')
    assert approx(sw_auc(0)[1]) == -16.454917436089122

    sw_ptp = sw.to_data('ptp')
    assert approx(sw_ptp(0)[1]) == 84.0
