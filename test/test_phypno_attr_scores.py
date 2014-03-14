from inspect import stack
from logging import getLogger
from nose.tools import raises
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

data_dir = '/home/gio/tools/phypno/data'

#-----------------------------------------------------------------------------#
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

def test_get_epochs():
    lg.info('---\nfunction: ' + stack()[0][3])

    sc.set_stage_for_epoch('30', 'NREM1')
    epochs = sc.get_epochs()
    assert len(epochs) == 159
    assert isinstance(epochs, dict)
    assert epochs['30']['stage'] == 'NREM1'


@raises(KeyError)
def test_scores_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    sc.set_stage_for_epoch('xxx', 'NREM2')

def test_scores_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    makedirs(dirname(temp_scores_file))
    Scores(temp_scores_file, sc.root)
