from inspect import stack
from logging import getLogger, DEBUG
from nose.tools import raises
from os.path import abspath, join
from numpy.testing import assert_array_equal, assert_almost_equal
from subprocess import check_output

lg = getLogger('phypno')
lg.setLevel(DEBUG)
# try this: rev-parse HEAD
git_ver = check_output('git -C ../.git rev-parse HEAD',
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

import phypno
data_dir = abspath(join(phypno.__path__[0], '..', 'data'))
