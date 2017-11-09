from wonambi.trans import frequency, math
from wonambi.utils import create_data
from numpy.testing import assert_array_almost_equal
from scipy.signal import hann

import plotly.graph_objs as go

from .utils import save_plotly_fig


def test_trans_frequency_doc_01():

    # generate data
    data = create_data(n_chan=2, signal='sine', amplitude=1)

    traces = [
        go.Scatter(
            x=data.time[0],
            y=data(trial=0, chan='chan00'))
        ]
    layout = go.Layout(
        xaxis=dict(
            title='Time (s)'),
        yaxis=dict(
            title='Amplitude (V)'),
        )
    fig = go.Figure(data=traces, layout=layout)
    save_plotly_fig(fig, 'freq_01_data')

    # default options
    freq = frequency(data, detrend=None)

    traces = [
        go.Scatter(
            x=freq.freq[0],
            y=freq(trial=0, chan='chan00'))
        ]
    layout = go.Layout(
        xaxis=dict(
            title='Frequency (Hz)',
            range=(0, 20)),
        yaxis=dict(
            title='Amplitude (V<sup>2</sup>/Hz)'),
        )
    fig = go.Figure(data=traces, layout=layout)
    save_plotly_fig(fig, 'freq_02_freq')

    # Parseval's theorem
    p_time = math(data, operator_name=('square', 'sum'), axis='time')
    p_freq = math(freq, operator_name='sum', axis='freq')
    assert_array_almost_equal(p_time(trial=0), p_freq(trial=0) * data.s_freq)

    # generate very long data
    data = create_data(n_chan=1, signal='sine', time=(0, 100))
    freq = frequency(data, taper='hann', duration=1, overlap=0.5)

    traces = [
        go.Scatter(
            x=freq.freq[0],
            y=freq(trial=0, chan='chan00')),
        ]
    layout = go.Layout(
        xaxis=dict(
            title='Frequency (Hz)',
            range=(0, 20)),
        yaxis=dict(
            title='Amplitude (V<sup>2</sup>/Hz)'),
        )
    fig = go.Figure(data=traces, layout=layout)
    save_plotly_fig(fig, 'freq_03_welch')

    # dpss
    data = create_data(n_chan=1, signal='sine')
    freq = frequency(data, taper='dpss', halfbandwidth=5)

    traces = [
        go.Scatter(
            x=freq.freq[0],
            y=freq(trial=0, chan='chan00')),
        ]
    layout = go.Layout(
        xaxis=dict(
            title='Frequency (Hz)',
            range=(0, 20)),
        yaxis=dict(
            title='Amplitude (V<sup>2</sup>/Hz)'),
        )
    fig = go.Figure(data=traces, layout=layout)
    save_plotly_fig(fig, 'freq_04_dpss')

    # ESD
    DURATION = 2
    data = create_data(n_chan=1, signal='sine', time=(0, DURATION))
    data.data[0][0, :] *= hann(data.data[0].shape[1])

    traces = [
        go.Scatter(
            x=data.time[0],
            y=data(trial=0, chan='chan00'))
        ]
    layout = go.Layout(
        xaxis=dict(
            title='Time (s)'),
        yaxis=dict(
            title='Amplitude (V)'),
        )
    fig = go.Figure(data=traces, layout=layout)
    save_plotly_fig(fig, 'freq_05_esd')

    freq = frequency(data, detrend=None, scaling='energy')

    traces = [
        go.Scatter(
            x=freq.freq[0],
            y=freq(trial=0, chan='chan00'))
        ]
    layout = go.Layout(
        xaxis=dict(
            title='Frequency (Hz)',
            range=(0, 20)),
        yaxis=dict(
            title='Amplitude (V<sup>2</sup>)'),
        )
    fig = go.Figure(data=traces, layout=layout)
    save_plotly_fig(fig, 'freq_06_esd')

    # Parseval's theorem
    p_time = math(data, operator_name=('square', 'sum'), axis='time')
    p_freq = math(freq, operator_name='sum', axis='freq')
    assert_array_almost_equal(p_time(trial=0), p_freq(trial=0) * data.s_freq * DURATION)

    # Complex
    data = create_data(n_chan=1, signal='sine')
    freq = frequency(data, output='complex', sides='two', scaling='energy')

    traces = [
        go.Scatter(
            x=freq.freq[0],
            y=abs(freq(trial=0, chan='chan00', taper=0)))
        ]
    layout = go.Layout(
        xaxis=dict(
            title='Frequency (Hz)'
            ),
        yaxis=dict(
            title='Amplitude (V)'),
        )
    fig = go.Figure(data=traces, layout=layout)
    save_plotly_fig(fig, 'freq_07_complex')
