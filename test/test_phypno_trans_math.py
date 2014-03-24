from . import *

from numpy import power, mean, std

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


def test_math_operator_name_on_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    apply_mean = Math(operator_name='mean', axis='time')
    data1 = apply_mean(data)

    assert len(data1.axis) == data1.data[0].ndim
    assert len(data1.axis['chan'][0]) == data1.data[0].shape[0]

    apply_mean = Math(operator_name='mean', axis='chan')
    data1 = apply_mean(data)

    assert len(data1.axis) == data1.data[0].ndim
    assert len(data1.axis['time'][0]) == data1.data[0].shape[0]


@raises(TypeError)
def test_math_incorrectly_on_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    Math(operator=mean)


@raises(TypeError)
def test_math_incorrectly_on_axis_tuple():
    lg.info('---\nfunction: ' + stack()[0][3])

    Math(operator_name=('square', 'mean', 'sqrt'))


def test_math_operator_name_tuple():
    lg.info('---\nfunction: ' + stack()[0][3])

    apply_hilb = Math(operator_name=('hilbert', 'abs'), axis='time')
    data1 = apply_hilb(data)
    assert data1.data[0].shape == data.data[0].shape


def test_math_operator_name_tuple_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    apply_rms = Math(operator_name=('square', 'mean', 'sqrt'),
                     axis='time')
    apply_rms(data)


@raises(ValueError)
def test_math_twice_on_same_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    apply_meanstd = Math(operator_name=('mean', 'std'),
                         axis='time')
    apply_meanstd(data)


def test_math_lambda():
    lg.info('---\nfunction: ' + stack()[0][3])

    p3 = lambda x: power(x, 3)
    apply_p3 = Math(operator=(p3, ))
    apply_p3(data)


def test_math_lambda_with_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    std_ddof = lambda x, axis: std(x, axis, ddof=1)
    apply_std = Math(operator=std_ddof, axis='time')
    apply_std(data)
