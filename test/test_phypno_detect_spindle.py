from . import *

from numpy import array
from numpy.testing import assert_array_equal

from phypno import Dataset
from phypno.attr import Scores
from phypno.detect import DetectSpindle
from phypno.detect.spindle import _detect_start_end

ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
scores_file = join(data_dir, 'MGXX/doc/scores',
                   'MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml')

score = Scores(scores_file)
N2_sleep = score.get_epochs(('NREM2', 'NREM3'))


dataset = Dataset(ktlx_dir)
data = dataset.read_data(chan=['GR' + str(x) for x in range(1, 11)],
                         begtime=N2_sleep[0]['start_time'],
                         endtime=N2_sleep[0]['end_time'])


def test_detect_start_end():
    lg.info('---\nfunction: ' + stack()[0][3])
    x = array([0, 0, 0, 0, 0, 0, 0, 0])
    assert_array_equal(_detect_start_end(x), None)

    x = array([0, 0, 0, 1, 0, 0, 0, 0])
    assert_array_equal(_detect_start_end(x), array([[3, 4]]))

    x = array([1, 0, 0, 0, 0, 0, 0, 0])
    assert_array_equal(_detect_start_end(x), array([[0, 1]]))

    x = array([0, 0, 0, 0, 0, 0, 0, 1])
    assert_array_equal(_detect_start_end(x), array([[7, 8]]))

    x = array([1, 0, 0, 0, 0, 0, 0, 1])
    assert_array_equal(_detect_start_end(x), array([[0, 1], [7, 8]]))


def test_detect_housestyle():
    lg.info('---\nfunction: ' + stack()[0][3])

    detsp = DetectSpindle(method='housestyle',
                          frequency=(10, 16), duration=(0.5, 2))
    sp = detsp(data)
    assert len(sp.spindle) == 29
