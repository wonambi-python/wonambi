from numpy.random import seed

from wonambi.utils import create_data
from wonambi.trans import concatenate


seed(0)
data = create_data(n_trial=5)


def test_concatenate_trial():
    data1 = concatenate(data, axis='trial')
    assert data1.number_of('trial') == 1
    assert data1.list_of_axes == ('chan', 'time', 'trial_axis')


def test_concatenate_axis():
    data1 = concatenate(data, axis='time')
    assert data1.number_of('time')[0] == data.number_of('time')[0] * data.number_of('trial')
