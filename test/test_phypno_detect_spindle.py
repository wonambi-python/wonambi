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

#-----------------------------------------------------------------------------#

from phypno.graphoelement import Spindle
from phypno.detect import DetectSpindle


def test_spindle_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    det_sp = DetectSpindle()
    sp = det_sp(None)
    assert isinstance(sp, Spindle)
