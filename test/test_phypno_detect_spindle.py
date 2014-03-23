from . import *

from os.path import join

from phypno import Dataset
from phypno.attr import Scores
from phypno.detect import DetectSpindle
from phypno.trans import Filter, Math

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

filter_sp = Filter(low_cut=11, high_cut=16, s_freq=data.s_freq)
apply_abs_hilb = Math(operator_name=('hilbert', 'abs'))

spindle_envelope = apply_abs_hilb(filter_sp(data))


def test_spindle_absolute_thres():
    lg.info('---\nfunction: ' + stack()[0][3])

    det_sp = DetectSpindle(threshold_type='absolute',
                           detection_threshold=0.05,
                           selection_threshold=0.02)

    spindles = det_sp(spindle_envelope)
    assert len(spindles.spindle) == 116


def test_spindle_no_detection():
    lg.info('---\nfunction: ' + stack()[0][3])

    det_sp = DetectSpindle(threshold_type='absolute',
                           detection_threshold=1.5,
                           selection_threshold=0.02)

    spindles = det_sp(spindle_envelope)
    assert len(spindles.spindle) == 0