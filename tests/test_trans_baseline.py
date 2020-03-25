from wonambi import Dataset
from wonambi.trans import math, select, frequency, apply_baseline
from numpy import array
from numpy.testing import assert_array_almost_equal

from .paths import micromed_file


def test_baseline():

    d = Dataset(micromed_file)
    ev = [ev['start'] for ev in d.read_markers()][1]
    chans = d.header['chan_name'][:2]
    data = d.read_data(events=ev, pre=1, post=1, chan=chans)

    time_interval = (-.5, -.1)
    out = apply_baseline(data, time=time_interval)
    mout = math(select(out, time=time_interval), operator_name='mean', axis='time')
    assert_array_almost_equal(mout(trial=0), array([1, 1]))

    out = apply_baseline(data, time=time_interval, baseline='zscore')
    mout = math(select(out, time=time_interval), operator_name='mean', axis='time')
    assert_array_almost_equal(mout(trial=0), array([0, 0]))

    out = apply_baseline(data, time=time_interval, baseline='percent')
    mout = math(select(out, time=time_interval), operator_name='mean', axis='time')
    assert_array_almost_equal(mout(trial=0), array([0, 0]))

    freq_interval = (10, 15)
    freq = frequency(data)
    out = apply_baseline(freq, freq=freq_interval, baseline='dB')
    mout = math(select(out, freq=freq_interval), operator_name='mean', axis='freq')
    assert_array_almost_equal(mout(trial=0), array([0, 0]))

    out = apply_baseline(freq, freq=freq_interval, baseline='normchange')
    assert out.data[0].max() <= 1
    assert out.data[0].min() >= -1
