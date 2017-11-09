from wonambi.utils import create_data
from numpy import arange, pi, sqrt, cos, sum
from scipy.signal.spectral import _spectral_helper
from numpy.random import seed
from numpy.testing import assert_array_equal, assert_array_almost_equal, assert_almost_equal

from wonambi.trans.frequency import _fft
from wonambi.trans import frequency, math, timefrequency


CORRECTION_FACTOR = 2 / 3

dur = 2
s_freq = 256


def test_trans_frequency():
    seed(0)
    data = create_data(n_trial=1, n_chan=2, s_freq=s_freq, time=(0, dur))
    # the first channel is ~5 times larger than the second channel
    data.data[0][0, :] *= 5

    # with random data, parseval only holds with boxcar
    freq = frequency(data, detrend=None, taper=None, scaling='power')
    p_time = math(data, operator_name=('square', 'sum'), axis='time')
    p_freq = math(freq, operator_name='sum', axis='freq')

    assert_array_almost_equal(p_time(trial=0), p_freq(trial=0) * s_freq)

    # one channel is 5 times larger than the other channel,
    # the square of this relationship should hold in freq domain
    freq = frequency(data, detrend=None, taper=None, scaling='power', duration=1)
    p_freq = math(freq, operator_name='sum', axis='freq')
    assert 4.7 ** 2 < (p_freq.data[0][0] / p_freq.data[0][1]) < (5.4 ** 2)

    freq = frequency(data, detrend=None, taper=None, scaling='energy', duration=1)
    p_freq = math(freq, operator_name='sum', axis='freq')
    assert 4.7 ** 2 < (p_freq.data[0][0] / p_freq.data[0][1]) < (5.4 ** 2)

    freq = frequency(data, detrend=None, taper='dpss', scaling='power')
    p_freq = math(freq, operator_name='sum', axis='freq')
    assert 4.7 ** 2 < (p_freq.data[0][0] / p_freq.data[0][1]) < (5.4 ** 2)

    freq = frequency(data, detrend=None, sides='two')
    p_freq = math(freq, operator_name='sum', axis='freq')
    assert 4.7 ** 2 < (p_freq.data[0][0] / p_freq.data[0][1]) < (5.45 ** 2)


def test_trans_frequency_complex():
    seed(0)
    data = create_data(n_trial=1, n_chan=2, s_freq=s_freq, time=(0, dur))
    NW = 3
    freq = frequency(data, output='complex', taper='dpss', NW=NW)
    assert freq.list_of_axes == ('chan', 'freq', 'taper')
    assert freq.data[0].shape == (data.number_of('chan')[0], dur * s_freq, NW * 2 - 1)


def test_trans_timefrequency_spectrogram():
    seed(0)
    data = create_data(n_trial=1, n_chan=2, s_freq=s_freq, time=(0, dur))
    # the first channel is ~5 times larger than the second channel
    data.data[0][0, :] *= 5

    timefreq = timefrequency(data, method='spectrogram', detrend=None, taper=None, overlap=0)
    p_time = math(data, operator_name=('square', 'sum'), axis='time')
    p_freq = math(timefreq, operator_name='sum', axis='freq')
    assert (4.7 ** 2 < p_freq.data[0][0, :] / p_freq.data[0][1, :]).all()
    assert (p_freq.data[0][0] / p_freq.data[0][1] < 5.7 ** 2).all()

    # with random data, parseval only holds with boxcar
    assert_array_almost_equal(p_time(trial=0), sum(p_freq(trial=0) * data.s_freq, axis=1))


def test_trans_timefrequency_stft():
    seed(0)
    data = create_data(n_trial=1, n_chan=2, s_freq=s_freq, time=(0, dur))
    NW = 3
    timefreq = timefrequency(data, method='stft', taper='dpss', NW=NW)
    assert timefreq.list_of_axes == ('chan', 'time', 'freq', 'taper')
    assert timefreq.data[0].shape == (data.number_of('chan')[0], 3, s_freq, NW * 2 - 1)


seed(0)
data = create_data(n_trial=1, n_chan=2, s_freq=s_freq, time=(0, dur), amplitude=10)
x = data(trial=0, chan='chan00')


def test_fft_spectrum_01():
    f, t, Sxx = _spectral_helper(x, x, fs=s_freq,
                                 window='hann',
                                 nperseg=x.shape[0],
                                 noverlap=0,
                                 nfft=None,
                                 return_onesided=True,
                                 mode='psd',
                                 scaling='density')

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', scaling='power', sides='one')

    assert_array_equal(f0, f)
    assert_array_almost_equal(Sxx0, Sxx[:, 0])


def test_fft_spectrum_02():
    """Scipy does not correct the energy with the spectrum scaling
    when windowing."""
    f, t, Sxx = _spectral_helper(x, x, fs=s_freq,
                                 window='hann',
                                 nperseg=x.shape[0],
                                 noverlap=0,
                                 nfft=None,
                                 return_onesided=True,
                                 mode='psd',
                                 scaling='spectrum')

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', scaling='energy', sides='one')

    assert_array_equal(f0, f)
    assert_array_almost_equal(Sxx0, Sxx[:, 0] * CORRECTION_FACTOR)


def test_fft_spectrum_03():
    f, t, Sxx = _spectral_helper(x, x, fs=s_freq,
                                 window='hann',
                                 nperseg=x.shape[0],
                                 noverlap=0,
                                 nfft=None,
                                 return_onesided=False,
                                 mode='psd',
                                 scaling='density')

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', scaling='power', sides='two')

    assert_array_equal(f0, f)
    assert_array_almost_equal(Sxx0, Sxx[:, 0])


def test_fft_spectrum_04():
    f, t, Sxx = _spectral_helper(x, x, fs=s_freq,
                                 window='hann',
                                 nperseg=x.shape[0],
                                 noverlap=0,
                                 nfft=None,
                                 return_onesided=False,
                                 mode='psd',
                                 scaling='spectrum')

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', scaling='energy', sides='two')

    assert_array_equal(f0, f)
    assert_array_almost_equal(Sxx0, Sxx[:, 0] * CORRECTION_FACTOR)


def test_fft_spectrum_05():
    f, t, Sxx = _spectral_helper(x, x, fs=s_freq,
                                 window='hann',
                                 nperseg=x.shape[0],
                                 noverlap=0,
                                 nfft=None,
                                 return_onesided=False,
                                 mode='stft',
                                 scaling='density')

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', scaling='power', output='complex', sides='two')

    assert_array_equal(f0, f)
    # in scipy, the extra dim is time, in wonambi it's the taper
    assert_array_almost_equal(Sxx0[:, 0], Sxx[:, 0])


def test_fft_spectrum_06():
    f, t, Sxx = _spectral_helper(x, x, fs=s_freq,
                                 window='hann',
                                 nperseg=x.shape[0],
                                 noverlap=0,
                                 nfft=None,
                                 return_onesided=False,
                                 mode='stft',
                                 scaling='spectrum')

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', scaling='energy', output='complex', sides='two')

    assert_array_equal(f0, f)
    # in scipy, the extra dim is time, in wonambi it's the taper
    assert_array_almost_equal(Sxx0[:, 0], Sxx[:, 0] * sqrt(CORRECTION_FACTOR))


def test_fft_spectrum_fieldtrip_01():
    """cfg = [];
    cfg.method = 'mtmfft';
    cfg.taper = 'dpss';
    cfg.tapsmofrq = 3;
    cfg.output = 'pow';
    freq = ft_freqanalysis(cfg, data);
    freq.powspctrm(1, 101:110)
    """
    ft_psd_dpss_3 = [0.00513886191307729, 0.00541235129368216, 0.00637327754180630, 0.00975873992634912, 0.0114961627430138, 0.0121812348620110, 0.0114278017545212, 0.0113668316543143, 0.0112161528645388, 0.0117016241464867]
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='spectraldensity', sides='one', scaling='fieldtrip', halfbandwidth=3)
    assert_array_almost_equal(Sxx0[100:110], ft_psd_dpss_3, decimal=4)


def test_fft_spectrum_fieldtrip_02():
    """cfg = [];
    cfg.method = 'mtmfft';
    cfg.taper = 'hanning';
    cfg.output = 'pow';
    freq = ft_freqanalysis(cfg, data);
    freq.powspctrm(1, 101:110)
    """
    ft_psd_hann = [0.00106465976843528, 0.00562957700710057, 0.00214937527201723, 0.000405599433993590, 0.00506141871942431, 0.00343922341551741, 0.00223373256323887, 0.00767611770955874, 0.0426550524445195, 0.0376986963169514]
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', output='spectraldensity', sides='one', scaling='fieldtrip')
    # less precise because different shape of hann window
    assert_array_almost_equal(Sxx0[100:110], ft_psd_hann, decimal=3)


def test_fft_spectrum_fieldtrip_03():
    """cfg = [];
    cfg.method = 'mtmfft';
    cfg.taper = 'dpss';
    cfg.tapsmofrq = 3;
    cfg.output = 'fourier';
    freq = ft_freqanalysis(cfg, data);
    transpose(squeeze(freq.fourierspctrm(1, 1, 101:110)))
    """
    ft_complex_dpss = [-0.0335619899491902 - 0.0100985443725351j, 0.0252013706875434 + 0.0436725973183397j, -0.0145928652426528 - 0.0546311601211480j, -0.00364680778007352 + 0.0542853721812055j, 0.0293189825468446 - 0.0554598147669454j, -0.0523346938092935 + 0.0458447745674979j, 0.0739055167896313 - 0.00673071060189224j, -0.0892965233534656 - 0.0698942934418098j, 0.0664933718921557 + 0.148311783870617j, -0.00190172379532472 - 0.160711901636832j]
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='complex', sides='two', scaling='fieldtrip', halfbandwidth=3)
    # Note that the DC freq is different
    assert_array_almost_equal(Sxx0[100:110, 0], ft_complex_dpss)


def test_fft_spectrum_chronux_01():
    """params = [];
    params.Fs = 256;
    [S, f] = mtspectrumc(data.trial{1}, params);
    """
    chronux_dpss = [0.0102448436805737, 0.0135297939292628, 0.0109646321153904, 0.0244494853313761, 0.0242404346616887, 0.0283518525147273, 0.0271608206918445, 0.0209374596495892, 0.0106591592406998, 0.00849276807621278]
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='spectraldensity', sides='one', scaling='chronux', NW=3)
    assert_array_almost_equal(chronux_dpss, Sxx0[:10])


def test_fft_spectrum_parseval_01():
    """energy should be equal in time and freq domain.
    """
    s_freq = 512
    dur = 3
    t = arange(0, dur, 1 / s_freq)
    F0 = 36
    A = 2
    x = A * cos(F0 * t * 2 * pi)

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper=None, output='spectraldensity', sides='one', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper=None, output='spectraldensity', sides='two', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper=None, output='complex', sides='two', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0 ** 2).real * s_freq)

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper=None, output='spectraldensity', sides='one', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq * dur)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper=None, output='spectraldensity', sides='two', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq * dur)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper=None, output='complex', sides='two', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0 ** 2).real * s_freq * dur)

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', output='spectraldensity', sides='one', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', output='spectraldensity', sides='two', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', output='complex', sides='two', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0 ** 2).real * s_freq)

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', output='spectraldensity', sides='one', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq * dur)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', output='spectraldensity', sides='two', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq * dur)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='hann', output='complex', sides='two', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0 ** 2).real * s_freq * dur)

    # dpss correction is not very precise but good enough
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='spectraldensity', sides='one', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq, 1)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='spectraldensity', sides='two', scaling='power')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq, 1)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='complex', sides='two', scaling='power')
    assert_almost_equal(sum(x ** 2), (Sxx0 ** 2).sum().real * s_freq, -1)

    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='spectraldensity', sides='one', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq * dur, 1)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='spectraldensity', sides='two', scaling='energy')
    assert_almost_equal(sum(x ** 2), sum(Sxx0) * s_freq * dur, 1)
    f0, Sxx0 = _fft(x, s_freq, detrend=None, taper='dpss', output='complex', sides='two', scaling='energy')
    assert_almost_equal(sum(x ** 2), (Sxx0 ** 2).sum().real * s_freq * dur, -1)


def test_fft_multiple_chan():

    x_chan = data(trial=0)  # both channels

    f, Sxx = _fft(x, data.s_freq, detrend=None)
    f, Sxx_chan = _fft(x_chan, data.s_freq, detrend=None)
    assert_array_equal(Sxx, Sxx_chan[0, ...])

    f, Sxx = _fft(x, data.s_freq, detrend=None, sides='two', output='complex')
    f, Sxx_chan = _fft(x_chan, data.s_freq, detrend=None, sides='two', output='complex')
    assert_array_equal(Sxx, Sxx_chan[0, ...])
