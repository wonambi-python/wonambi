Event detection
===============

Wonambi can automatically detect sleep spindles and slow waves in the signal.

To detect events, make sure you have first loaded a Montage and an Annotation File.
In your Montage, create the desired channels for event detection. Note that filters set in the Channels tab are not retained for event detection.
Now, click on ``Analysis`` -> ``Detect`` and choose the desired event. This will open the detection dialog. 

Let's start with the **spindle detection dialog**:

.. image:: images/notes_16_spindledialog.png

Info
----

Under ``Label``, enter the name of this event type, which will appear on the trace. 
You may choose an existing event type or create a new one. 
If you choose an existing event type, existing events of this type will be preserved.

Next, you will see ``Channel group`` and ``Channel(s)``. 
You may perform automatic detection on several channels at once, within a same group. 
Select the desired group from the drop-down menu, and the desired channel(s). 
Select several channels by holding down the ``Ctrl`` key.

If you have delimited cycles (see :ref:`notes`), the cycle indices will appear under ``Cycle(s)``. 
You may select one or several cycles.
If no cycle is selected, detection will ignore cycles.

Under ``Stage(s)``, select in which stage or stages to find events. 
If no stage is selected, detection will ignore stages.

.. WARNING::
   If you select neither a cycle nor a stage, detection will be carried out over the entire record, even wake!

Parameters
----------

You may select among a number of spindle detection algorithms in the ``Method`` drop-down menu.
The parameter values will be updated to the values reported in the source literature.
These values remain fully customizable.

Note that not all method parameters are applicable to each method. 
In these cases, the method parameter is grayed out and marked ``N/A``.

For details about the implemented algorithms, see below.

Options
-------

If you have marked certain epochs as having *Poor* signal, you may check ``Exclude Poor signal epochs`` to remove them from the detection signal.

Similarly, if you have marked events with event type *Artefact*, you may check the ``Exclude Artefact events`` box to remove them from the detection signal.
Signal on all selected channels that is concurrent with an *Artefact* event on any channel will be excluded from detection. 

Signal selection and rejection may result in a fragmented signal, especially when excluding *Artefact* events.
You may set a minimum duration for these fragments with ``Minimum subsegment duration``. 
Signal fragments shorter than this value will be excluded.
All remaining fragments are then concatenated (within a same channel) to create the detection signal.

If you selected several channels, you may choose to merge spindles detected in close proximity across channels with ``Merge events across channels``.
When this option is selected, spindles on different channels that are separated by less than a specified delay will be merged onto the channel with the earliest onset spindle.
The delay is set with ``Minimum interval``, under *Parameters*. If ``Minimum interval`` is set to zero, only overlapping spindles will be merged.

The **slow wave detection dialog** is similar to the spindle detection dialog:

.. image:: images/notes_17_slowwavedialog.png

As in the spindle dialog, you can choose a slow wave detection algorithm from the ``Method`` drop-down menu, and the parameters will update with default values from the source literature.
Note that the ``AASM/Massimini_2004`` method is identical to the ``Massimini_2004`` algorithm, but with different default values for the method parameters.
For details about the implemented algorithms, consult the ``Help`` box, accessible at the bottom of the dialog.

The ``De-mean`` checkbox subtracts the mean of the detection signal for each channel.

The ``Invert detection`` checkbox allows you to "flip" the detection algorithm upside-down, so that instead of a "trough-then-peak" pattern, it will look for a "peak-then-trough" pattern.

For conceptual reasons, there is no option to merge events during slow wave detection.

Detection methods
-----------------

The method options in the spindle and slow wave detection dialogs are direct implementations of detection methods reported in the scholarly articles cited below.

Original values for the customizable parameters are provided in square brackets [].

Further details on the original methods are provided in italics.

.. NOTE::
   Italicized steps are not automatically implemented in Wonambi's algorithms.
   They are included only for your information.

*Spindle detection methods*

**Wamsley2012** - *Wamsley, E. J. et al. (2012) Biol. Psychiatry 71, 154-61*

#. *Detection is limited to NREM2 signal, filtered between 0.5-35 Hz.*
#. The artifact-free EEG signal is subjected to a time-frequency transformation using an 8-parameter complex Morlet wavelet with the average of ``Lowcut`` and ``Highcut`` as the frequency, with σ = ``Wavelet sigma`` [0.5] s and with window size = ``Detection window`` [1] s.
#. The resulting complex-valued time series is squared.
#. The imaginary component of the time-series is discarded, and the remaining real-valued time series is squared again.
#. The moving average of the real signal is calculated, using a sliding window of size = ``Smoothing`` [0.1] s.
#. A spindle event is identified whenever this wavelet signal exceeds a threshold, defined as ``Detection threshold, low`` [4.5] times the mean signal amplitude of all artifact-free epochs, between ``Min. duration`` [0.4] s and ``Max. duration`` s [no maximum]. In this implementation, threshold crossings define the spindle start and end times, but see next point for the original method.
#. *The duration of each spindle was calculated as the half-height width of wavelet energy within the spindle frequency range.*

**Mölle2011** - *Mölle, M. et al. (2011) Sleep 34(10), 1411-21*

#. *Detection is limited to NREM signal.*
#. Signal is bandpass filtered between ``Lowcut`` and ``Highcut``, using a zero-phase equiripple FIR filter. Authors specify -3 dB attenuation at 11.3 and 15.7 Hz (Mölle et al., J Neurosci, 2002). To achieve this, ``Lowcut`` and ``Highcut`` must be set to 12 Hz and 15 Hz, and ``Roll-off`` to 1.7 Hz.
#. The root-mean-square of the signal is taken, with a moving window of size = ``Detection window`` [0.2] s.
#. The resulting RMS signal is smoothed with a moving average of window size = ``Smoothing`` [0.2] s.
#. The detection threshold is set to the mean of the RMS signal + ``Detection threshold, low`` [1.5] x RMS signal SD.
#. Spindles are detected as a continuous rise in the smoothed RMS signal above the detection threshold lasting between ``Min. duration`` [0.5] s and ``Max. duration`` [3] s. Spindle start and end times are the threshold crossings.

**Nir2011** - *Nir, Y. et al. (2011) Neuron 70, 153-69*

#. *The channels with spindle activity in NREM sleep are chosen for further analysis (significant spectral power increases in spindle range as compared with a 1/f model, p ‹ 0.001, paired t-test across 10 s segments.)*
#. The EEG signal is bandpass filtered between ``Lowcut`` Hz and ``Highcut`` Hz with a zero-phase 4th order Butterworth filter. Authors specify -3 dB attenuation at 9.2 Hz and 16.8 Hz. To achieve this with a 4th order filter, ``Lowcut`` and ``Highcut`` must be set to 9.2 Hz and 16.8 Hz, respectively.
#. Instantaneous amplitude in the sigma frequency is extracted via the Hilbert transform.
#. To avoid excessive multiple crossings of thresholds within the same spindle event, instantaneous amplitude is temporally smoothed using a Gaussian kernel of σ = ``Smoothing`` [0.4] s.
#. Events with amplitude greater than mean + ``Detection threshold, low`` [3] SD (computed across all artifact-free NREM sleep epochs) are considered putative spindles and detections within ``Min. interval`` [1] s are merged.
#. A threshold of mean + ``Selection threshold`` [1] SD defines start and end times, and events with duration between ``Min. duration`` [0.5] s and ``Max. duration`` [2] s are selected for further analysis.
#. *Those channels, in which an increase in spectral power within the detected events was restricted to the spindle-frequency range (10-16 Hz) rather than broadband (unpaired t-test (α=0.001) between maximal spectral power in detected vs. random events), and with at least 1 spindle per min of NREM sleep were chosen for further analysis. This highly conservative procedure of including in the analysis only the channels with high spindle SNR, ensured that local occurrence of spindle events does not arise merely as a result of the lack of spindles or poor spindle SNR in some channels.*

**Ferrarelli2007** - *Ferrarelli, F. et al. (2007) Am. J. Psychiatry 164, 483-92*

#. *Detection is limited to all NREM sleep signal.*
#. Signal is bandpass filtered between ``Lowcut`` and ``Highcut`` with a zero-phase equiripple Chebyshev FIR filter. Authors used a slightly different and less stable Chebyshev Type II IIR filter. The FIR filter is a more stable approximation. With ``Lowcut`` at 11 Hz, ``Highcut`` at 15 Hz and ``Roll-off`` at 0.9 Hz, the attenuation is -3 dB at 10.7 Hz and 15.3 Hz.
#. The filtered signal is rectified.
#. A signal envelope is created from the oscillatory peaks in the rectified signal.
#. The detection threshold is set to the mean of the signal envelope x ``Detection threshold, low`` [8].
#. For the selection threshold, the signal envelope amplitude values are distributed in a 120-bin histogram, and the amplitude of the highest-count bin x ``Selection threshold`` [2] yields the selection threshold.
#. Spindles are detected where the signal envelope exceeds the detection threshold, with start and end times where the envelope dips below the selection threshold, before and after the detected peak.
#. Spindles are merged if within ``Min. interval`` (or overlapping).
#. Spindles within ``Min. duration`` and ``Max. duration`` are retained.

**Concordia** - *Concordia University, Montreal; unpublished*

#. Signal is bandpass filtered between ``Lowcut`` and ``Highcut`` with a zero-phase 6th order Butterworth filter.
#. The root-mean-square of the signal is taken, with a moving window of size = ``Detection window`` [0.2] s.
#. The resulting RMS signal is smoothed with a moving average of window size = ``Smoothing`` [0.2] s.
#. The low and high detection thresholds are set at the mean of the RMS signal + ``Detection threshold, low`` [1.5] x RMS signal SD, and mean + ``Detection threshold, high`` [10] x SD, respectively.
#. RMS rises between the low and high detection thresholds are considered putative spindles, and those located within ``Min. interval`` [0.2] s are merged.
#. A threshold of mean + ``Selection threshold`` [1] SD defines start and end times, and events with duration between ``Min. duration`` [0.5] s and ``Max. duration`` [2] s are selected for further analysis.

**UCSD** - *University of California, San Diego; unpublished*

#. The raw EEG signal is subjected to a time-frequency transformation using real wavelets with frequencies from ``Lowcut`` to ``Highcut`` at 0.5-Hz intervals, with width = 0.5 s and with window size = ``Detection window`` [1] s.
#. The resulting time-frequency signals are rectified and convolved with a Tukey window of size = 0.5 s, then averaged to produce a single time-frequency signal.
#. A threshold is defined as the signal median plus ``Detection threshold, low`` [2] SDs.
#. Spindles are detected at each relative maximum in the signal which exceeds the threshold.
#. Steps 1-3 are repeated on the raw signal, this time with width = 0.2 s, with Tukey window size = 0.2 s, and with the threshold set at ``Selection threshold`` [1] SD.
#. Spindle start and end times are defined at threshold crossings.
#. Spindles are retained if their duration is between ``Min. duration`` and ``Max. duration``.

*Slow wave detection methods*

**Massimini2004** - *Massimini, M. et al. (2004) J Neurosci 24(31), 6862-70*

#. *256-channel EEG is re-referenced to the average of the signals from the earlobes.*
#. *EEG signal is locally averaged over 4 non-overlapping regions of the scalp.*
#. *Detection is limited to NREM signal.*
#. The signal is bandpass filtered between ``Lowcut`` and ``Highcut``, using a zero-phase 4th order Butterworth filter. Wonambi's implementation applies the filter sequentially to avoid numerical instability: first lowpass, the highpass.
#. Slow waves are detected when the following 3 criteria are met:
   * A negative zero crossing and a subsequent positive zero crossing separated by ``Min. trough duration`` [0.3] and ``Max. trough duration`` [1.0] s.
   * A negative peak between the two zero crossings with voltage less than ``Max. trough amplitude`` [-80] μV
   * A negative-to-positive peak-to-peak amplitude greater than ``Min. peak-to-peak amplitude`` [140] μV.

**AASM/Massimini2004**

This is a reimplementation of Massimini et al., 2004 (above), except with default values for slow waves as defined by the American Academy of Sleep Medicine (AASM).

