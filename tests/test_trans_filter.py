from numpy.random import seed
from pytest import raises

from wonambi.utils import create_data
from wonambi.trans import filter_, frequency, convolve


seed(0)
data = create_data(n_trial=1)


def test_filter_errors():
    with raises(ValueError):
        filter_(data, low_cut=1000)

    with raises(ValueError):
        filter_(data, high_cut=1000)

    with raises(ValueError):
        filter_(data, low_cut=1000, high_cut=10)

    with raises(TypeError):
        filter_(data)


def test_filter():
    filter_(data, low_cut=10, high_cut=100)
    filter_(data, high_cut=100)
    filter_(data, low_cut=100)


def test_filter_notch():
    filt = filter_(data, ftype='notch')

    freq_data = frequency(data)
    freq_filt = frequency(filt)

    assert (freq_data(trial=0, freq=50) > freq_filt(trial=0, freq=50)).all()


def test_convolve():
    convolve(data, 'hann')
