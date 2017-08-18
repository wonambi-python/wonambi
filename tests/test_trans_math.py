from numpy import power, mean, nanmax, std
from numpy.testing import assert_array_equal
from pytest import raises

from wonambi.trans import math
from wonambi.utils import create_data


data = create_data(n_trial=10)


def test_math_incompatible_parameters():

    with raises(TypeError):
        math(operator_name=('square'), operator=(power))


def test_math_operator_name():

    data1 = math(data, operator_name='square')
    assert_array_equal(data1.data[0] ** .5, abs(data.data[0]))


def test_math_operator_name_on_axis():

    data1 = math(data, operator_name='mean', axis='time')

    assert len(data1.axis) == data1.data[0].ndim
    assert len(data1.axis['chan'][0]) == data1.data[0].shape[0]

    data1 = math(data, operator_name='mean', axis='chan')

    assert len(data1.axis) == data1.data[0].ndim
    assert len(data1.axis['time'][0]) == data1.data[0].shape[0]


def test_math_incorrectly_on_axis():

    with raises(TypeError):
        math(operator=mean)


def test_math_incorrectly_on_axis_tuple():

    with raises(TypeError):
        math(operator_name=('square', 'mean', 'sqrt'))


def test_math_operator_name_tuple():

    data1 = math(data, operator_name=('hilbert', 'abs'), axis='time')
    assert data1.data[0].shape == data.data[0].shape


def test_math_operator_name_tuple_axis():

    data1 = math(data, operator_name=('square', 'mean', 'sqrt'), axis='time')
    assert data1.data[0].shape == (data.number_of('chan')[0], )


def test_math_twice_on_same_axis():

    with raises(ValueError):
        math(data, operator_name=('mean', 'std'), axis='time')


def test_math_lambda():

    p3 = lambda x: power(x, 3)
    math(data, operator=(p3, ))


def test_math_lambda_with_axis():

    std_ddof = lambda x, axis: std(x, axis, ddof=1)
    math(data, operator=std_ddof, axis='time')


def test_own_funct():

    def func(x, axis, keepdims=None):
        return nanmax(x, axis=axis)

    m_data = math(data, operator=func, axis='time')
    assert len(m_data.list_of_axes) == 1


def test_math_diff():

    data1 = math(data, operator_name='diff', axis='time')

    # shape should not change
    assert_array_equal(data1.data[0].shape, data.data[0].shape)
    assert_array_equal(data1.data[-1].shape, data.data[-1].shape)

    # check that the values are correct
    dat = data(trial=0, chan='chan01')[2] - data(trial=0, chan='chan01')[1]
    dat1 = data1(trial=0, chan='chan01')[2]
    assert dat == dat1
