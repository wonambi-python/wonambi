from inspect import stack
from logging import getLogger
from nose.tools import raises
from numpy.testing import assert_array_equal, assert_array_almost_equal
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

data_dir = '/home/gio/tools/phypno/data'

#-----------------------------------------------------------------------------#
from numpy import power, exp, mean

from phypno.trans import Math
from phypno.utils import create_data


data = create_data(n_trial=10)

@raises(TypeError)
def test_math_incompatible_parameters():
    lg.info('---\nfunction: ' + stack()[0][3])

    Math(operator_name=('square'), operator=(power))


def test_math_operator_name():
    lg.info('---\nfunction: ' + stack()[0][3])

    apply_sqrt = Math(operator_name='square')
    data1 = apply_sqrt(data)
    assert_array_equal(data1.data[0] ** .5, data.data[0])


def test_math_incorrectly_on_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    mean_on_axis = lambda x: mean(x, axis=0)
    apply_sqrt = Math(operator=mean_on_axis)
    data1 = apply_sqrt(data)


def test_math_operator_name_tuple():
    lg.info('---\nfunction: ' + stack()[0][3])

    apply_hilb = Math(operator_name=('hilbert', 'abs'))
    data1 = apply_hilb(data)


def test_math_lambda():
    lg.info('---\nfunction: ' + stack()[0][3])

    p3 = lambda x: power(x, 3)
    apply_p3 = Math(operator=(p3, ))
    apply_p3(data)


def test_math_datafreq():
    lg.info('---\nfunction: ' + stack()[0][3])

    datafreq = create_data(datatype='DataFreq')

    apply_log = Math(operator_name='log')
    datafreq1 = apply_log(datafreq)
    assert_array_almost_equal(exp(datafreq1.data[0]), datafreq.data[0])
