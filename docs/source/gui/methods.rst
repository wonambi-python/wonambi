Detection methods
=================

The method options in the spindle and slow wave detection dialogs are direct implementations of detection methods reported in the scholarly articles cited below.
These implementations are based on original author code when available.

Original values for the customizable parameters are provided in square brackets [].

Further details on the original methods are provided in italics.

.. NOTE::
   Italicized steps are not automatically implemented in Wonambi's algorithms.
   They are included only for your information.

Spindle detection methods
-------------------------

**Ferrarelli2007** - *Ferrarelli, F. et al. (2007) Am. J. Psychiatry 164, 483-92*

#. *Detection is limited to all NREM sleep signal.*
#. Signal is bandpass filtered between ``Lowcut`` and ``Highcut`` with a zero-phase equiripple Chebyshev FIR filter. Authors used a slightly different and less stable Chebyshev Type II IIR filter. The FIR filter is a more stable approximation. With ``Lowcut`` at 11 Hz, ``Highcut`` at 15 Hz and ``Roll-off`` at 0.9 Hz, the attenuation is -3 dB at 10.7 Hz and 15.3 Hz.
#. The filtered signal is rectified.
#. A signal envelope is created from the oscillatory peaks in the rectified signal.
#. The detection threshold is set to the mean of the signal envelope x ``Detection threshold`` [8].
#. For the selection threshold, the signal envelope amplitude values are distributed in a 120-bin histogram, and the amplitude of the highest-count bin x ``Selection threshold`` [2] yields the selection threshold.
#. Spindles are detected where the signal envelope exceeds the detection threshold, with start and end times where the envelope dips below the selection threshold, before and after the detected peak.
#. Spindles are merged if within ``Min. interval`` [0] s of each other (or overlapping).
#. Spindles within ``Min. duration`` and ``Max. duration`` are retained.

**Nir2011** - *Nir, Y. et al. (2011) Neuron 70, 153-69*

#. *The channels with spindle activity in NREM sleep are chosen for further analysis (significant spectral power increases in spindle range as compared with a 1/f model, p ‹ 0.001, paired t-test across 10 s segments.)*
#. The EEG signal is bandpass filtered between ``Lowcut`` Hz and ``Highcut`` Hz with a zero-phase 4th (2x2) order Butterworth filter. Authors specify -3 dB attenuation at 9.2 Hz and 16.8 Hz. To achieve this with a 4th order filter, ``Lowcut`` and ``Highcut`` must be set to 9.2 Hz and 16.8 Hz, respectively.
#. Instantaneous amplitude in the sigma frequency is extracted via the Hilbert transform.
#. To avoid excessive multiple crossings of thresholds within the same spindle event, instantaneous amplitude is temporally smoothed using a Gaussian kernel of σ = ``Gaussian smoothing sigma`` [0.4] s.
#. Events with amplitude greater than mean + ``Detection threshold`` [3] SD (computed across all *artifact-free NREM sleep* epochs) are considered putative spindles and detections within ``Min. interval`` [1] s of each other are merged.
#. A threshold of mean + ``Selection threshold`` [1] SD defines start and end times, and events with duration between ``Min. duration`` [0.5] s and ``Max. duration`` [2] s are selected for further analysis.
#. *Those channels, in which an increase in spectral power within the detected events was restricted to the spindle-frequency range (10-16 Hz) rather than broadband (unpaired t-test (α=0.001) between maximal spectral power in detected vs. random events), and with at least 1 spindle per min of NREM sleep were chosen for further analysis. This highly conservative procedure of including in the analysis only the channels with high spindle SNR, ensured that local occurrence of spindle events does not arise merely as a result of the lack of spindles or poor spindle SNR in some channels.*

**Mölle2011** - *Mölle, M. et al. (2011) Sleep 34(10), 1411-21*

#. *Detection is limited to NREM signal.*
#. Signal is bandpass filtered between ``Lowcut`` and ``Highcut``, using a zero-phase equiripple FIR filter. Authors specify -3 dB attenuation at 11.3 and 15.7 Hz (Mölle et al., J Neurosci, 2002). To achieve this, ``Lowcut`` and ``Highcut`` must be set to 12 Hz and 15 Hz, and ``Roll-off`` to 1.7 Hz.
#. The root-mean-square of the signal is taken, with a moving window of size = ``RMS window length`` [0.2] s.
#. The resulting RMS signal is smoothed with a moving average of window size = ``Smoothing window length`` [0.2] s.
#. The detection threshold is set to the mean of the RMS signal + ``Detection threshold`` [1.5] x RMS signal SD.
#. Spindles are detected as a continuous rise in the smoothed RMS signal above the detection threshold lasting between ``Min. duration`` [0.5] s and ``Max. duration`` [3] s. Spindle start and end times are the threshold crossings.
#. Spindles are merged if within ``Min. interval`` [0] s of each other.

**Wamsley2012** - *Wamsley, E. J. et al. (2012) Biol. Psychiatry 71, 154-61*

#. *Detection is limited to NREM2 signal, filtered between 0.5-35 Hz.*
#. The *artefact-free* EEG signal is subjected to a time-frequency transformation using an 8-parameter complex Morlet wavelet with the average of ``Lowcut`` and ``Highcut`` as the frequency, with σ = ``Wavelet sigma`` [0.5] s and with window size = ``Wavelet window length`` [1] s.
#. The resulting complex-valued time series is squared.
#. The imaginary component of the time-series is discarded, and the remaining real-valued time series is squared again.
#. The moving average of the real signal is calculated, using a sliding window of size = ``Smoothing window length`` [0.1] s.
#. A spindle event is identified whenever this wavelet signal exceeds a threshold, defined as ``Detection threshold`` [4.5] times the mean signal amplitude of all artefact-free epochs, between ``Min. duration`` [0.4] s and ``Max. duration`` s [no maximum]. In this implementation, threshold crossings define the spindle start and end times, but see next point for the original method.
#. *The duration of each spindle was calculated as the half-height width of wavelet energy within the spindle frequency range.*
#. Spindles are merged if within ``Min. interval`` [0] s of each other.

**Martin2013** - *Martin, N. et al. (2013) Neurobio. Aging 34(2) 468-76*

#. *Artefact-free NREM sleep epochs are retained for analysis.*
#. Signal is bandpass-filtered between ``Lowcut`` and ``Highcut`` with a zero-phase equiripple Chebyshev FIR filter. The authors used a slightly different filter, but this implementation is more stable, and with the default lowcut and highcut and a ``Roll-off`` of 0.4 Hz, -3 dB attenuation is achieved at 11.1 Hz and 14.9 Hz.
#. The root-mean-square of the filtered signal is taken for every consecutive window of duration ``RMS window length`` [0.25] s and of step ``RMS window step`` [None] s.
#. The detection threshold is set at percentile ``Detection threshold`` [95] of the RMS signal.
#. Spindles are detected when the RMS signal exceeds the detection threshold for longer than ``Min. duration`` [0.5] s and shorter than ``Max. duration`` [3] s.
#. Spindles are merged if within ``Min. interval`` [0] s of each other.


**Ray2015** - *Ray, L. B. et al. (2015) Front. Hum. Neurosci. 9-16*

#. The *artefact-free* signal is bandpass filtered between 0.3 Hz and 35 Hz, using a zero-phase 8th (4x2) order Butterworth filter.
#. Complex demodulation is deployed on the data about the frequency of interest, set by the mean of ``Lowcut`` [11] and ``Highcut`` [16] (Hz).
#. The complex demodulated signal is lowpass filtered below 5 Hz, using a zero-phase 8th (4x2) order Butterworth filter.
#. The lowpass filtered signal is smoothed using a triangle convolution, with window size set by ``Smoothing window length`` [2 / frequency of interest] (sec).
#. The square of the absolute value of the complex, smoothed signal is taken.
#. The resulting signal is converted into a z-score signal, with a sliding window set by ``zscore window length`` [60] (sec).
#. Spindles are detected where the z-score signal exceeds ``Detection threshold`` [2.33].
#. Spindle start and end times are defined where the z-score signal surrounding a detected spindle drops below ``Selection threshold`` [0.1].
#. Spindles separated by less than ``Min. interval`` [0.25] sec are merged. *Instead of merging spindles, authors excluded spindles beginning less than 0.25 s after of a detected spindle.*
#. Spindles within ``Min. duration`` [0.49] sec and ``Max. duration`` [None] are retained.

**Lacourse2018** - *Lacourse, K. et al. (2018) J Neurosci. Meth.*

#. *Artefact-free NREM sleep epochs are retained for analysis.*
#. Signal is bandpass filtered between ``Lowcut`` and ``Highcut`` to create the sigma signal, and between 0.3 Hz and 30 Hz to create the broadband signal.
#. All transformations are applied to the windowed signal, with a window duration of ``Window length`` [0.3] s and with a step of ``Window step`` [0.1] s.
#. The absolute sigma power signal is taken as the window average of the squared value of each data sample. The resulting signal is log10-transformed.
#. The relative sigma power signal is taken as the ratio of sigma band power to broadband power, log10-transformed and z-score normalized with respect to a 30-s window centered on the current window. In computing the z-score, only values between the 10th and 90th percentile are used to compute the standard deviation.
#. The covariance signal is taken as the window average of the sample-wise product of the detrended sigma signal and detrended broadband signal.
#. The normalized covariance signal is taken as the covariance signal log10-transformed and z-score normalized with respect to the 30-s window centered on the current window.  In computing the z-score, only values between the 10th and 90th percentile are used to compute the standard deviation.
#. The correlation signal is taken as the covariance signal divided, window-wise, by the product of the standard deviations of the sigma and broadband signals.
#. Spindles are detected when all four of these conditions are met:

   * the absolute sigma power signal exceeds ``Absolute power threshold`` [1.25];
   * the relative sigma power signal exceeds ``Relative sigma threshold`` [1.6];
   * the normalized covariance signal exceeds ``Covariance threshold`` [1.3];
   * the correlation signal exceeds ``Correlation threshold`` [0.69].
   
#. Spindle start and end times are defined where the normalized covariance and correlation signals surrounding a detected spindle drop below their respective threshold.
#. Spindles shorter than ``Min. duration`` [0.3] s and ``Max. duration`` [2.5] s are discarded.
#. Spindles are merged if within ``Min. interval`` [0] s of each other.

#. *A context classifier, based on the spectral makeup of the signal surrounding each detected spindle, identifies those spindles likely to be true positives. This step (not implemented) is most useful in the absence of sleep staging.*

**FASST** - *Leclerq, Y. et al. (2011) Compu. Intel. Neurosci. 1-11*

#. Signal is bandpass filtered between ``Lowcut`` [11] and ``Highcut`` [18] using a zero-phase 8th (4x2) order Butterworth filter.
#. The detection threshold is set as the ``Detection threshold`` th percentile of the filtered signal. *Authors use only N2 signal to set the threshold.*
#. The filtered signal is rectified, yielding the detection signal.
#. The detection signal is smoothed with a moving average of window size = ``Smoothing window length`` [0.1].
#. Spindles are detected as rises in the detection signal above the detection threshold, lasting between ``Min. duration`` [0.4] and ``Max. duration`` [1.3].
#. Detected spindles separated by less than ``Min. interval`` [1] s are merged.
#. *Spindles overlapping across channels are merged.*

**FASST2** - *Leclerq, Y. et al. (2011) Compu. Intel. Neurosci. 1-11*

This method is identical to FASST, except step 3 is replaced with the following step:

3. The root-mean-square of the filtered signal is taken, with a moving window of size = ``RMS window length`` [0.1] s, yielding the detection signal.

**UCSD** - *University of California, San Diego; unpublished*

#. The raw EEG signal is subjected to a time-frequency transformation using real wavelets with frequencies from ``Lowcut`` to ``Highcut`` at 0.5-Hz intervals, with wavelet duration = ``Wavelet duration`` [1] s, width = ``Wavelet width`` s and smoothing window duration = ``Smoothing window length``.
#. The resulting time-frequency signals are rectified and convolved with a Tukey window of size = 0.5 s, then averaged to produce a single time-frequency signal.
#. A threshold is defined as the signal median plus ``Detection threshold`` [2] SDs.
#. Spindles are detected at each relative maximum in the signal which exceeds the threshold.
#. Steps 1-3 are repeated on the raw signal, this time with width = 0.2 s, with Tukey window size = 0.2 s, and with the threshold set at ``Selection threshold`` [1] SD.
#. Spindle start and end times are defined at threshold crossings.
#. Spindles are retained if their duration is between ``Min. duration`` and ``Max. duration``.
#. Spindles are merged if within ``Min. interval`` [0] s of each other.

**Concordia** - *Concordia University, Montreal; unpublished*

#. Signal is bandpass filtered between ``Lowcut`` and ``Highcut`` with a zero-phase 6th (3x2) order Butterworth filter.
#. The root-mean-square of the signal is taken, with a moving window of size = ``RMs window length`` [0.2] s.
#. The resulting RMS signal is smoothed with a moving average of window size = ``Smoothing window length`` [0.2] s.
#. The low and high detection thresholds are set at the mean of the RMS signal + ``Detection threshold`` [1.5] x RMS signal SD, and mean + ``Detection threshold`` [10] x SD, respectively.
#. RMS rises between the low and high detection thresholds are considered putative spindles, and those located within ``Tolerance`` [0.2] s are merged.
#. A threshold of mean + ``Selection threshold`` [1] SD defines start and end times, and events with duration between ``Min. duration`` [0.5] s and ``Max. duration`` [2] s are selected for further analysis.
#. Spindles are merged if within ``Min. interval`` [0] s of each other.

Slow wave detection methods
---------------------------

**Massimini2004** - *Massimini, M. et al. (2004) J Neurosci 24(31), 6862-70*

#. *256-channel EEG is re-referenced to the average of the signals from the earlobes.*
#. *EEG signal is locally averaged over 4 non-overlapping regions of the scalp.*
#. *Detection is limited to NREM signal.*
#. The signal is bandpass filtered between ``Lowcut`` and ``Highcut``, using a zero-phase 4th (2x2) order Butterworth filter. Wonambi's implementation applies the filter sequentially to avoid numerical instability: first lowpass, the highpass.
#. Slow waves are detected when the following 3 criteria are met:

   * A positive-to-negative zero crossing and a subsequent negative-to-positive zero crossing separated by ``Min. trough duration`` [0.3] and ``Max. trough duration`` [1.0] s.
   * A negative peak between the two zero crossings with voltage less than ``Max. trough amplitude`` [-80] μV
   * A peak-to-peak amplitude greater than ``Min. peak-to-peak amplitude`` [140] μV.

.. NOTE::
   Not all channels will show slow waves with the same polarity (e.g. F3-M2 and M2-F3 will be inverted).
   Furthermore, the typical iEEG channels will show slow waves as positive-then-negative, contrary to surface EEG electrodes.
   For these reasons, it is left to the user to set the correct polarity for slow wave detection.
   The default polarity is negative-then-positive. 
   Wonambi displays signals negative-up, so on typical EEG channels, slow waves will be up-then-down.
   To switch to positive-then-negative (down-then-up), check the ``Invert detection`` box.

**AASM/Massimini2004**

This is the same as Massimini2004, except with default values for slow waves as defined by the American Academy of Sleep Medicine (AASM).
