from . import *

from os import makedirs
from os.path import join, dirname
from tempfile import mkdtemp

from phypno.attr import Scores

scores_file = join(data_dir, 'MGXX/doc/scores',
                   'MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml')
temp_scores_file = join(mkdtemp(), 'MGXX/doc/scores',
                        'MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml')


sc = Scores(scores_file)


def test_scores_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    assert sc.get_rater() == 'gio'
    sc.set_stage_for_epoch('30', 'NREM2')
    assert sc.get_stage_for_epoch('30') == 'NREM2'


def test_get_epochs_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    sc.get_epochs(('NREM1', 'NREM2'))
    assert len(sc.get_epochs(('xxx'))) == 0


def test_get_epochs():
    lg.info('---\nfunction: ' + stack()[0][3])

    sc.set_stage_for_epoch('30', 'NREM1')
    epochs = sc.get_epochs()

    # implementation details
    assert len(epochs) == 159
    assert isinstance(epochs, list)
    epochs = sorted(epochs, key=lambda x: x['start_time'])
    assert epochs[1]['stage'] == 'NREM1'


@raises(KeyError)
def test_scores_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    sc.set_stage_for_epoch('xxx', 'NREM2')


def test_scores_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    makedirs(dirname(temp_scores_file))
    Scores(temp_scores_file, sc.root)






