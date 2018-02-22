"""Module to compute frequency representation.
"""
from copy import deepcopy
from logging import getLogger
from warnings import warn

from numpy import (arange, array, empty, exp, max, mean, pi, real, sqrt,
                   swapaxes)
from numpy.linalg import norm
import numpy.fft as np_fft
from scipy import fftpack
from scipy.signal import windows, get_window, fftconvolve
from scipy.signal import detrend as detrend_func

from .extern.dpss import dpss_windows  # this will be in scipy v1.1
from ..datatype import ChanFreq, ChanTimeFreq
from .select import _create_subepochs

lg = getLogger(__name__)


def frequency(data, output='spectraldensity', scaling='power', sides='one',
              taper=None, halfbandwidth=3, NW=None, duration=None, 
              overlap=0.5, step=None, detrend='linear', n_smp=None):
    """Compute the
    power spectral density (PSD, output='spectraldensity', scaling='power'), or
    energy spectral density (ESD, output='spectraldensity', scaling='energy') or
    the complex fourier transform (output='complex', sides='two')

    Parameters
    ----------
    data : instance of ChanTime
        one of the datatypes
    detrend : str
        None (no detrending), 'constant' (remove mean), 'linear' (remove linear
        trend)
    output : str
        'spectraldensity' or 'complex'
    sides : str
        'one' or 'two', where 'two' implies negative frequencies
    scaling : str
        'power' (units: V ** 2 / Hz), 'energy' (units: V ** 2), 'fieldtrip',
        'chronux'
    taper : str
        Taper to use, commonly used tapers are 'boxcar', 'hann', 'dpss'
    halfbandwidth : int
        (only if taper='dpss') Half bandwidth (in Hz), frequency smoothing will
        be from +halfbandwidth to -halfbandwidth
    NW : int
        (only if taper='dpss') Normalized half bandwidth
        (NW = halfbandwidth * dur). Number of DPSS tapers is 2 * NW - 1.
        If specified, NW takes precedence over halfbandwidth
    duration : float, in s
        If not None, it divides the signal in epochs of this length (in seconds)
        and then average over the PSD / ESD (not the complex result)
    overlap : float, between 0 and 1
        The amount of overlap between epochs (0.5 = 50%, 0.95 = almost complete
        overlap).
    step : float, in s
        step in seconds between epochs (alternative to overlap)
    n_smp: int
        Length of FFT, in samples. If less than input axis, input is cropped.
        If longer than input axis, input is padded with zeros. If None, FFT
        length set to axis length.

    Returns
    -------
    instance of ChanFreq
        If output='complex', there is an additional dimension ('taper') which
        is useful for 'dpss' but it's also present for all the other tapers.

    Raises
    ------
    TypeError
        If the data does not have a 'time' axis. It might work in the
        future on other axes, but I cannot imagine how.

    ValueError
        If you use duration (to create multiple epochs) and output='complex',
        because it does not average the complex output of multiple epochs.

    Notes
    -----
    See extensive notes at wonambi.trans.frequency._fft

    It uses sampling frequency as specified in s_freq, it does not
    recompute the sampling frequency based on the time axis.
    """
    if 'time' not in data.list_of_axes:
        raise TypeError('\'time\' is not in the axis ' +
                        str(data.list_of_axes))
    if len(data.list_of_axes) != data.index_of('time') + 1:
        raise TypeError('\'time\' should be the last axis')  # this might be improved

    if duration is not None and output == 'complex':
        raise ValueError('cannot average the complex spectrum over multiple epochs')

    if duration is not None:
        nperseg = int(duration * data.s_freq)
        if step is not None:
            nstep = int(step * data.s_freq)
        else:
            nstep = nperseg - int(overlap * nperseg)

    freq = ChanFreq()
    freq.s_freq = data.s_freq
    freq.start_time = data.start_time
    freq.axis['chan'] = data.axis['chan']
    freq.axis['freq'] = empty(data.number_of('trial'), dtype='O')
    if output == 'complex':
        freq.axis['taper'] = empty(data.number_of('trial'), dtype='O')
    freq.data = empty(data.number_of('trial'), dtype='O')

    for i in range(data.number_of('trial')):
        x = data(trial=i)
        if duration is not None:
            x = _create_subepochs(x, nperseg, nstep)

        f, Sxx = _fft(x,
                      s_freq=data.s_freq,
                      detrend=detrend,
                      taper=taper,
                      output=output,
                      sides=sides,
                      scaling=scaling,
                      halfbandwidth=halfbandwidth,
                      NW=NW,
                      n_smp=n_smp)

        if duration is not None:
            Sxx = Sxx.mean(axis=-2)

        freq.axis['freq'][i] = f
        if output == 'complex':
            freq.axis['taper'][i] = arange(Sxx.shape[-1])
        freq.data[i] = Sxx

    return freq


def timefrequency(data, method='morlet', time_skip=1, **options):
    """Compute the power spectrum over time.

    Parameters
    ----------
    data : instance of ChanTime
        data to analyze
    method : str
        the method to compute the time-frequency representation, such as
        'morlet' (wavelet using complex morlet window),
        'spectrogram' (corresponds to 'spectraldensity' in frequency()),
        'stft' (short-time fourier transform, corresponds to 'complex' in
        frequency())
    options : dict
        options depend on the method used, see below.

    Returns
    -------
    instance of ChanTimeFreq
        data in time-frequency representation. The exact output depends on
        the method. Using 'morlet', you get a complex output at each frequency
        where the wavelet was computed.

    Examples
    --------
    The data in ChanTimeFreq are complex and they should stay that way. You
    can also get the magnitude or power the easy way using Math.

    >>> from wonambi.trans import math, timefreq
    >>> tf = timefreq(data, foi=(8, 10))
    >>> tf_abs = math(tf, operator_name='abs')
    >>> tf_abs.data[0][0, 0, 0]
    1737.4662329214384)

    Notes
    -----
    It uses sampling frequency as specified in s_freq, it does not
    recompute the sampling frequency based on the time axis.

    For method 'morlet', the following options should be specified:
        foi : ndarray or list or tuple
            vector with frequency of interest
        ratio : float
            ratio for a wavelet family ( = freq / sigma_f)
        sigma_f : float
            standard deviation of the wavelet in frequency domain
        dur_in_sd : float
            duration of the wavelet, given as number of the standard deviation
            in the time domain, in one side.
        dur_in_s : float
            total duration of the wavelet, two-sided (i.e. from start to
            finish)
        time_skip : int, in samples
            number of time points to skip (it runs convolution on all the
            data points, but you don't need to store them all)
        normalization : str
            'area' means that energy is normalized to 1, 'peak' means that the
            peak of the wavelet is set at 1, 'max' is a normalization used by
            nitime where the max value of the output of the convolution remains
            the same even if you change the sigma_f.
        zero_mean : bool
            make sure that the wavelet has zero mean (only relevant if ratio
            < 5)

    For method 'spectrogram' or 'stft', the following options should be specified:
        duraton : int
            duration of the window to compute the power spectrum, in s
        overlap : int
            amount of overlap (0 -> no overlap, 1 -> full overlap)
    """
    implemented_methods = ('morlet',
                           'spectrogram',  # this is output spectraldensity
                           'stft')  # this is output complex

    if method not in implemented_methods:
        raise ValueError('Method ' + method + ' is not implemented yet.\n'
                         'Currently implemented methods are ' +
                         ', '.join(implemented_methods))

    if method == 'morlet':
        default_options = {'foi': None,
                           'ratio': 5,
                           'sigma_f': None,
                           'dur_in_sd': 4,
                           'dur_in_s': None,
                           'normalization': 'area',
                           'zero_mean': False,
                           }
    elif method in ('spectrogram', 'stft'):
        default_options = {'duration': 1,
                           'overlap': 0.5,
                           'step': None,
                           'detrend': 'linear',
                           'taper': 'hann',
                           'sides': 'one',
                           'scaling': 'power',
                           'halfbandwidth': 2,
                           'NW': None,
                           }

    default_options.update(options)
    options = default_options

    timefreq = ChanTimeFreq()
    timefreq.s_freq = data.s_freq
    timefreq.start_time = data.start_time
    timefreq.axis['chan'] = data.axis['chan']
    timefreq.axis['time'] = empty(data.number_of('trial'), dtype='O')
    timefreq.axis['freq'] = empty(data.number_of('trial'), dtype='O')
    if method == 'stft':
        timefreq.axis['taper'] = empty(data.number_of('trial'), dtype='O')
    timefreq.data = empty(data.number_of('trial'), dtype='O')

    if method == 'morlet':

        wavelets = _create_morlet(deepcopy(options), data.s_freq)

        for i in range(data.number_of('trial')):
            lg.info('Processing trial # {0: 6}'.format(i))
            timefreq.axis['freq'][i] = array(options['foi'])
            timefreq.axis['time'][i] = data.axis['time'][i][::time_skip]

            timefreq.data[i] = empty((data.number_of('chan')[i],
                                      data.number_of('time')[i] // time_skip,
                                      len(options['foi'])),
                                     dtype='complex')
            for i_c, chan in enumerate(data.axis['chan'][i]):
                dat = data(trial=i, chan=chan)
                for i_f, wavelet in enumerate(wavelets):
                    tf = fftconvolve(dat, wavelet, 'same')
                    timefreq.data[i][i_c, :, i_f] = tf[::time_skip]

        if time_skip != 1:
            warn('sampling frequency in s_freq refers to the input data, '
                 'not to the timefrequency output')

    elif method in ('spectrogram', 'stft'):  # TODO: add timeskip
        nperseg = int(options['duration'] * data.s_freq)
        if options['step'] is not None:
            nstep = int(options['step'] * data.s_freq)
        else:
            nstep = nperseg - int(options['overlap'] * nperseg)

        if method == 'spectrogram':
            output = 'spectraldensity'
        elif method == 'stft':
            output = 'complex'

        for i in range(data.number_of('trial')):
            t = _create_subepochs(data.time[i], nperseg, nstep).mean(axis=1)
            x = _create_subepochs(data(trial=i), nperseg, nstep)

            f, Sxx = _fft(x,
                          s_freq=data.s_freq,
                          detrend=options['detrend'],
                          taper=options['taper'],
                          output=output,
                          sides=options['sides'],
                          scaling=options['scaling'],
                          halfbandwidth=options['halfbandwidth'],
                          NW=options['NW'])

            timefreq.axis['time'][i] = t
            timefreq.axis['freq'][i] = f
            if method == 'stft':
                timefreq.axis['taper'][i] = arange(Sxx.shape[-1])
            timefreq.data[i] = Sxx

    return timefreq


def _create_morlet(options, s_freq):
    """Create morlet wavelets, with scipy.signal doing the actual computation.

    Parameters
    ----------
    foi : ndarray or list or tuple
        vector with frequency of interest
    s_freq : int or float
        sampling frequency of the data
    options : dict
        with 'M_in_s' (duration of the wavelet in seconds) and 'w' (Omega0)

    Returns
    -------
    ndarray
        nFreq X nSamples matrix containing the complex Morlet wavelets.

    """
    wavelets = []
    foi = options.pop('foi')
    for f in foi:
        wavelets.append(morlet(f, s_freq, **options))

    return wavelets


def morlet(freq, s_freq, ratio=5, sigma_f=None, dur_in_sd=4, dur_in_s=None,
           normalization='peak', zero_mean=False):
    """Create a Morlet wavelet.

    Parameters
    ----------
    freq : float
        central frequency of the wavelet
    s_freq : int
        sampling frequency
    ratio : float
        ratio for a wavelet family ( = freq / sigma_f)
    sigma_f : float
        standard deviation of the wavelet in frequency domain
    dur_in_sd : float
        duration of the wavelet, given as number of the standard deviation in
        the time domain, in one side.
    dur_in_s : float
        total duration of the wavelet, two-sided (i.e. from start to finish)
    normalization : str
        'area' means that energy is normalized to 1, 'peak' means that the peak
        is set at 1, 'max' is a normalization used by nitime which does not
        change max value of output when you change sigma_f.
    zero_mean : bool
        make sure that the wavelet has zero mean (only relevant if ratio < 5)

    Returns
    -------
    ndarray
        vector containing the complex Morlet wavelets

    Notes
    -----
    'ratio' and 'sigma_f' are mutually exclusive. If you use 'sigma_f', the
    standard deviation stays the same for all the frequency. It's more common
    to specify a constant ratio for the wavelet family, so that the frequency
    resolution changes with the frequency of interest.

    'dur_in_sd' and 'dur_in_s' are mutually exclusive. 'dur_in_s' specifies the
    total duration (from start to finish) of the window. 'dur_in_sd' calculates
    the total duration as the length in standard deviations in the time domain:
    dur_in_s = dur_in_sd * 2 * sigma_t, with sigma_t = 1 / (2 * pi * sigma_f)
    """
    if sigma_f is None:
        sigma_f = freq / ratio
    else:
        ratio = freq / sigma_f
    sigma_t = 1 / (2 * pi * sigma_f)

    if ratio < 5 and not zero_mean:
        lg.info('The wavelet won\'t have zero mean, set zero_mean=True to '
                'correct it')

    if dur_in_s is None:
        dur_in_s = sigma_t * dur_in_sd * 2

    t = arange(-dur_in_s / 2, dur_in_s / 2, 1 / s_freq)

    w = exp(1j * 2 * pi * freq * t)
    if zero_mean:
        w -= exp(-1 / 2 * ratio ** 2)

    w *= exp(-t ** 2 / (2 * sigma_t ** 2))

    if normalization == 'area':
        w /= sqrt(sqrt(pi) * sigma_t * s_freq)
    elif normalization == 'max':
        w /= 2 * sigma_t * sqrt(2 * pi) / s_freq
    elif normalization == 'peak':
        pass

    lg.info('At freq {0: 9.3f}Hz, sigma_f={1: 9.3f}Hz, sigma_t={2: 9.3f}s, '
            'total duration={3: 9.3f}s'.format(freq, sigma_f, sigma_t,
                                               dur_in_s))
    lg.debug('    Real peak={0: 9.3f}, Mean={1: 12.6f}, '
             'Energy={2: 9.3f}'.format(max(real(w)), mean(w), norm(w) ** 2))

    return w


def _fft(x, s_freq, detrend='linear', taper=None, output='spectraldensity',
         sides='one', scaling='power', halfbandwidth=4, NW=None, n_smp=None):
    """
    Core function taking care of computing the power spectrum / power spectral
    density or the complex representation.

    Parameters
    ----------
    x : 1d or 2d numpy array
        input data (fft will be computed on the last dimension)
    s_freq : int
        sampling frequency
    detrend : str
        None (no detrending), 'constant' (remove mean), 'linear' (remove linear
        trend)
    output : str
        'spectraldensity' (= 'psd' in scipy) or 'complex' (for complex output)
    sides : str
        'one' or 'two', where 'two' implies negative frequencies
    scaling : str
        'power' (= 'density' in scipy, units: uV ** 2 / Hz),
        'energy' (= 'spectrum' in scipy, units: uV ** 2),
        'fieldtrip', 'chronux'
    taper : str
        Taper to use, commonly used tapers are 'boxcar', 'hann', 'dpss' (see
        below)
    halfbandwidth : int
        (only if taper='dpss') Half bandwidth (in Hz), frequency smoothing will
        be from +halfbandwidth to -halfbandwidth
    NW : int
        (only if taper='dpss') Normalized half bandwidth
        (NW = halfbandwidth * dur). Number of DPSS tapers is 2 * NW - 1.
        If specified, NW takes precedence over halfbandwidth
    n_smp: int
        Length of FFT, in samples. If less than input axis, input is cropped.
        If longer than input axis, input is padded with zeros. If None, FFT
        length set to axis length.

    Returns
    -------
    freqs : 1d ndarray
        vector with frequencies at which the PSD / ESD / complex fourier was
        computed
    result: ndarray
        PSD / ESD / complex fourier. It has the same number of dim as the input.
        Frequency transform is computed on the last dimension. If
        output='complex', there is one additional dimension with the taper(s).

    Notes
    -----
    The nomenclature of the frequency-domain analysis is not very consistent
    across packages / toolboxes. The convention used here is based on `wikipedia`_

    So, you can have the spectral density (called sometimes power spectrum) or
    a complex output. Conceptually quite different but they can both be computed
    using the fft algorithm, so we do both here.

    Regarding the spectral density, you can have the power spectral density
    (PSD) or the energy spectral density (ESD). PSD should be used for
    stationary signals (gamma activity), while ESD should be used for signals
    that have a clear beginning and end (spindles). ESD gives the energy over
    the whole duration of the input window, while PSD is normalized by the
    window length.

    Parseval's theorem says that the energy of the signal in the time-domain
    must be equal to the energy in the frequency domain. All the tapers are
    correct to comply with this theorem (see tests/test_trans_frequency.py for
    all the examples). Note that packages such as 'FieldTrip' and 'Chronux' do
    not usually respect this convention (and use some ad-hoc convention).
    You can use the scaling of these packages to compare the results from those
    matlab toolboxes, but note that the results probably don't satisty Parseval's
    theorem.

    Note that scipy.signal is not consistent with these names, but the
    formulas are the same. Also, scipy (v1.1 at least) does not handle dpss.

    Finally, the complex output has an additional dimension (taper), for each
    taper (even for the boxcar or hann taper). This is useful for multitaper
    analysis (DPSS), where it doesn't make sense to average complex results.

    .. _wikipedia:
        https://en.wikipedia.org/wiki/Spectral_density

    TODO
    ----
    Scipy v1.1 can generate dpss tapers. Once scipy v1.1 is available, use
    that instead of the extern folder.
    """
    if output == 'complex' and sides == 'one':
        print('complex always returns both sides')
        sides = 'two'

    axis = x.ndim - 1
    
    if n_smp is None:
        n_smp = x.shape[axis]

    if sides == 'one':
        freqs = np_fft.rfftfreq(n_smp, 1 / s_freq)
    elif sides == 'two':
        freqs = fftpack.fftfreq(n_smp, 1 / s_freq)

    if taper is None:
        taper = 'boxcar'

    if taper == 'dpss':
        if NW is None:
            NW = halfbandwidth * n_smp / s_freq
        tapers, eig = dpss_windows(n_smp, NW, 2 * NW - 1)
        if scaling == 'chronux':
            tapers *= sqrt(s_freq)

    else:
        if taper == 'hann':
            tapers = windows.hann(n_smp, sym=False)[None, :]
        else:
            # TODO: it'd be nice to use sym=False if possible, but the difference is very small
            tapers = get_window(taper, n_smp)[None, :]

        if scaling == 'energy':
            rms = sqrt(mean(tapers ** 2))
            tapers /= rms * sqrt(n_smp)
        elif scaling != 'chronux':
            # idk how chronux treats other windows apart from dpss
            tapers /= norm(tapers)

    if detrend is not None:
        x = detrend_func(x, axis=axis, type=detrend)
    tapered = tapers * x[..., None, :]

    if sides == 'one':
        result = np_fft.rfft(tapered, n=n_smp)
    elif sides == 'two':
        result = fftpack.fft(tapered, n=n_smp)

    if scaling == 'chronux':
        result /= s_freq
    elif scaling == 'fieldtrip':
        result *= sqrt(2 / n_smp)

    if output == 'spectraldensity':
        result = (result.conj() * result)

    if sides == 'one' and output == 'spectraldensity' and scaling != 'chronux':
        if n_smp % 2:
            result[..., 1:] *= 2
        else:
            # Last point is unpaired Nyquist freq point, don't double
            result[..., 1:-1] *= 2

    if scaling == 'power':
        scale = 1.0 / s_freq
    elif scaling == 'energy':
        scale = 1.0 / n_smp
    else:
        scale = 1
    if output == 'complex' and scaling in ('power', 'energy'):
        scale = sqrt(scale)
    result *= scale

    if scaling == 'fieldtrip' and output == 'spectraldensity':
        # fieldtrip uses only one side
        result /= 2

    if output == 'spectraldensity':
        result = result.real
        result = mean(result, axis=axis)
    elif output == 'complex':
        # dpss should be last dimension in complex, no mean
        result = swapaxes(result, axis, -1)

    return freqs, result
