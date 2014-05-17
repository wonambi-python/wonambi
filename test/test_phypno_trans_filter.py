from . import *

from numpy import log10, asarray
from scipy.signal import fftconvolve

from phypno import Dataset
from phypno.trans import Filter, Convolve
from phypno.utils import create_data


edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')
d = Dataset(edf_file)
data = d.read_data(chan=['LMF5', 'LMF6'], begtime=0, endtime=100)


@raises(TypeError)
def test_filter_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter()


def test_filter_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    f = Filter(low_cut=.1)
    f(data)


@raises(ValueError)
def test_filter_wrong_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    f = Filter(low_cut=.1)
    f(data, axis='chan')  # too short


@raises(ValueError)
def test_filter_nonexistent_axis():
    lg.info('---\nfunction: ' + stack()[0][3])

    f = Filter(low_cut=.1)
    f(data, axis='xxx')


def test_filter_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter(high_cut=.4)


def test_filter_04():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter(low_cut=.1, high_cut=.4)


def test_filter_05():
    lg.info('---\nfunction: ' + stack()[0][3])

    Filter(low_cut=.1, order=5)


def test_filter_06():
    lg.info('---\nfunction: ' + stack()[0][3])

    f1 = Filter(low_cut=10, s_freq=200)
    f2 = Filter(low_cut=.1)
    assert all(f1.a == f2.a)


def test_convolution_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    tapering = Convolve(window='boxcar', length=1, s_freq=data.s_freq)
    fdata = tapering(data)
    assert data.data[0].shape == fdata.data[0].shape

    # check that the values have the same magnitude
    m_data = log10(abs(sum(data.data[0].flatten())))
    m_fdata = log10(abs(sum(fdata.data[0].flatten())))
    assert_almost_equal(m_data, m_fdata, decimal=2)

    # check that running one channel is identical to the Convolve class
    # note that precision might change
    CHAN = data.axis['chan'][0][-1]
    cdat = fftconvolve(data(trial=0, chan=CHAN), tapering.taper, 'same')
    cdat32 = asarray(cdat, dtype=data.data[0].dtype)
    assert_array_equal(cdat32, fdata(trial=0, chan=CHAN))


def test_convolution_chantimefreq():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(datatype='ChanTimeFreq')

    tapering = Convolve(window='hanning', length=1, s_freq=data.s_freq)
    fdata = tapering(data)
    assert data.data[0].shape == fdata.data[0].shape

    # check that running one channel is identical to the Convolve class
    CHAN = data.axis['chan'][0][-1]
    FREQ = data.axis['freq'][0][10]
    cdat = fftconvolve(data(trial=0, chan=CHAN, freq=FREQ),
                       tapering.taper, 'same')
    assert_array_equal(cdat, fdata(trial=0, chan=CHAN, freq=FREQ))


def test_convolution_chantimefreq_another_dim():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(datatype='ChanTimeFreq')

    tapering = Convolve(window='hanning', length=1, s_freq=data.s_freq)
    fdata = tapering(data, axis='freq')
    assert data.data[0].shape == fdata.data[0].shape

    CHAN = data.axis['chan'][0][-1]
    TIME = data.axis['time'][0][10]
    cdat = fftconvolve(data(trial=0, chan=CHAN, time=TIME),
                       tapering.taper, 'same')
    assert_array_equal(cdat, fdata(trial=0, chan=CHAN, time=TIME))


@raises(AssertionError)
def test_convolution_chantimefreq_another_dim_fail():
    lg.info('---\nfunction: ' + stack()[0][3])

    data = create_data(datatype='ChanTimeFreq')

    tapering = Convolve(window='hanning', length=1, s_freq=data.s_freq)
    fdata = tapering(data, axis='freq')
    assert data.data[0].shape == fdata.data[0].shape

    # this should fail, convolve is on freq, but here we convolve on time axis
    CHAN = data.axis['chan'][0][-1]
    FREQ = data.axis['freq'][0][10]
    cdat = fftconvolve(data(trial=0, chan=CHAN, freq=FREQ),
                       tapering.taper, 'same')
    assert_array_equal(cdat, fdata(trial=0, chan=CHAN, freq=FREQ))
