from . import *

from phypno import Dataset
from phypno.attr import Scores
from phypno.detect import DetectSpindle
from phypno.trans import Math

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


def test_spindle_absolute_thres():
    lg.info('---\nfunction: ' + stack()[0][3])

    det_sp = DetectSpindle(threshold_type='absolute',
                           detection_threshold=0.5,
                           selection_threshold=0.2)
    spindles = det_sp(data)
    assert len(spindles.spindle) == 272


def test_spindle_no_detection():
    lg.info('---\nfunction: ' + stack()[0][3])

    det_sp = DetectSpindle(threshold_type='absolute',
                           detection_threshold=10,
                           selection_threshold=1)

    spindles = det_sp(data)
    assert len(spindles.spindle) == 0


def test_spindle_relative_thres():
    lg.info('---\nfunction: ' + stack()[0][3])

    det_sp = DetectSpindle(threshold_type='relative',
                           frequency=(11, 20),
                           detection_threshold=3,
                           selection_threshold=1)
    spindles = det_sp(data)
    assert len(spindles.spindle) == 47
