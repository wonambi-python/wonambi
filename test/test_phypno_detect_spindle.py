# from test import *

from sys import path
path[3] = '/home/gio/tools/detsp'

from os.path import join
data_dir = '/home/gio/tools/phypno/data'


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



self = DetectSpindle(method='housestyle', frequency=(11, 18), duration=(0.5, 2))

self.basic = {'data': ('morlet_interval', 'moving_avg'),
              'opt': ((9, 20), 1)}
self.psd_peak['use'] = False
sp = self(data)
len(sp.spindle)

# peak values are still different


dat_orig = data(trial=0, chan='GR1')




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


def test_spindle_absolute_thres():
    lg.info('---\nfunction: ' + stack()[0][3])

    OPTIONS = {'frequency': (11, 20),
               'method': 'hilbert',
               'method_options': {},
               'threshold': 'absolute',
               'threshold_options': {'detection_value': 0.5,
                                     'selection_value': 0.2,
                                     },
               'criteria': {'duration': (.5, 2),
                            },
               }
    det_sp = DetectSpindle(**OPTIONS)
    spindles = det_sp(data)

    assert len(spindles.spindle) == 93


def test_spindle_no_detection():
    lg.info('---\nfunction: ' + stack()[0][3])

    OPTIONS = {'frequency': (11, 20),
               'method': 'hilbert',
               'method_options': {},
               'threshold': 'absolute',
               'threshold_options': {'detection_value': 10,
                                     'selection_value': 1,
                                     },
               'criteria': {'duration': (.5, 2),
                            },
               }
    det_sp = DetectSpindle(**OPTIONS)
    spindles = det_sp(data)

    assert len(spindles.spindle) == 0


def test_spindle_relative_thres():
    lg.info('---\nfunction: ' + stack()[0][3])

    OPTIONS = {'frequency': (11, 20),
               'method': 'hilbert',
               'method_options': {},
               'threshold': 'relative',
               'threshold_options': {'detection_value': 3,
                                     'selection_value': 1,
                                     },
               'criteria': {'duration': (.5, 2),
                            },
               }
    det_sp = DetectSpindle(**OPTIONS)
    spindles = det_sp(data)
    assert len(spindles.spindle) == 7


def test_spindle_peak_in_fft():
    lg.info('---\nfunction: ' + stack()[0][3])

    OPTIONS = {'frequency': (11, 20),
               'method': 'hilbert',
               'method_options': {},
               'threshold': 'relative',
               'threshold_options': {'detection_value': 3,
                                     'selection_value': 1,
                                     },
               'criteria': {'peak_in_fft': {'length': 1,
                                            }
                            },
               }

    det_sp = DetectSpindle(**OPTIONS)
    spindles = det_sp(data)
    assert len(spindles.spindle) == 16


def test_spindle_wavelet():
    lg.info('---\nfunction: ' + stack()[0][3])

    OPTIONS = {'frequency': (9, 20),
               'method': 'wavelet',
               'method_options': {'detection_wavelet': {'M_in_s': 1,
                                                        'w': 7,
                                                        },
                                  'detection_smoothing': {'window': 'boxcar',
                                                          'length': 1,
                                                          },
                                  },
               'threshold': 'maxima',
               'threshold_options': {'peak_width': 1,
                                     'select_width': 1,
                                     },
               'criteria': {'duration': (.5, 2),
                            'peak_in_fft': {'length': 1,
                                            },
                            },
               }
    det_sp = DetectSpindle(**OPTIONS)
    spindles = det_sp(data)
    assert len(spindles.spindle) == 18
