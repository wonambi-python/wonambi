from inspect import stack
from logging import getLogger, DEBUG, INFO, WARNING, CRITICAL
from nose.plugins.attrib import attr
from nose.tools import raises
from os.path import abspath, join
from numpy.testing import assert_array_equal, assert_almost_equal, assert_array_almost_equal
from subprocess import check_output

lg = getLogger('phypno')
lg.setLevel(INFO)

import phypno
data_dir = abspath(join(phypno.__path__[0], '..', 'data'))

