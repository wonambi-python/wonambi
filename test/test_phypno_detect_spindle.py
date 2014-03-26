from . import *

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
apply_abs_hilb = Math(operator_name=('hilbert', 'abs'), axis='time')

filtered = filter_sp(data)
spindle_envelope = apply_abs_hilb(filtered)


@raises(TypeError)
def test_spindle_type_error_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    DetectSpindle(threshold_type='absolute',
                  detection_threshold=(1, 1))


@raises(TypeError)
def test_spindle_type_error_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    DetectSpindle(threshold_type='absolute',
                  detection_threshold=1,
                  selection_threshold=(1, 1))


@raises(TypeError)
def test_spindle_type_error_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    DetectSpindle(threshold_type='relative',
                  detection_threshold=1)


@raises(TypeError)
def test_spindle_type_error_04():
    lg.info('---\nfunction: ' + stack()[0][3])

    DetectSpindle(threshold_type='relative',
                  detection_threshold=(1, 1),
                  selection_threshold=1)


def test_spindle_absolute_thres():
    lg.info('---\nfunction: ' + stack()[0][3])

    det_sp = DetectSpindle(threshold_type='absolute',
                           detection_threshold=0.5,
                           selection_threshold=0.2)
    spindles = det_sp(spindle_envelope)

    assert len(spindles.spindle) == 116


def test_spindle_no_detection():
    lg.info('---\nfunction: ' + stack()[0][3])

    det_sp = DetectSpindle(threshold_type='absolute',
                           detection_threshold=1.5,
                           selection_threshold=0.02)

    spindles = det_sp(spindle_envelope)
    assert len(spindles.spindle) == 0


def test_spindle_relative_thres():
    lg.info('---\nfunction: ' + stack()[0][3])

    get_mean = Math(operator_name='mean', axis='time')
    get_std = Math(operator_name='std', axis='time')

    envelope_mean = get_mean(filtered)
    envelope_std = get_std(filtered)

    detection_threshold = envelope_mean(trial=0) + envelope_std(trial=0) * 3
    selection_threshold = envelope_mean(trial=0) + envelope_std(trial=0) * 1.5

    det_sp = DetectSpindle(threshold_type='relative',
                           detection_threshold=detection_threshold,
                           selection_threshold=selection_threshold)
    spindles = det_sp(spindle_envelope)
    assert len(spindles.spindle) == 4
