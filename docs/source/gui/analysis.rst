Analysis console
================

Wonambi's analysis console allows the flexible selection of signal for a variety of analyses, including frequency domain analyses and phase-amplitude coupling (PAC).
Signal can be selected by event, epoch or longest run, and by channel, cycle and stage, with flexible concatenation options, and with artefacted signal exclusion.

To open the dialog, click on ``Analysis`` -> ``Analysis console``.

.. image:: images/analysis_01_dialog.png

File location
-------------

Select the base name and location of the data files. The analysis console creates CSV files containing the raw analysis data.

.. NOTE::
   These data files can become quite large depending on the analysis.

Chunking
--------

Different analyses require different lengths of signal, hence the chunking option. You may chunk by ``event``, ``epoch`` or ``longest run``.

Chunking ``by event`` gathers all events of the type(s) selected as individual segments.
If you wish to gather only the signal for the channel on which an event was marked, keep the ``Channel-specific`` box checked.
Alternatively, you may wish to gather signal concurrent to an event on all selected channels (channel selection is below).
In this case uncheck ``Channel-specific''.

Chunking ``by epoch`` gathers all relevant signal cut up into segments of equal duration.
To obtain the epochs as segmented by the Annotation file for sleep scoring, check ``Lock to staging epochs``.
Otherwise, you may select a different epoch length with ``Duration (sec)``. 
In this case, all relevant signal, after the specified concatenation, will be segmented at that duration, starting at the first sample of relevant signal.
Any remainder is discarded.

Chunking ``by longest run`` gathers all relevant signal cut up into the longest continuous (uninterrupted) segments.
For instance, if in the sleep cycle selected there is a run of 10 minutes of REM, with another isolated 30s epoch of REM cut off from the rest, this option will return two segments, one 10 minutes long and one 30s long.

Location
--------

Next, you will see ``Channel group`` and ``Channel(s)``. You may select signal from several channels within a same group. 

If you have delimited cycles (see notes_), the cycle indices will appear under ``Cycle(s)``. You may select one or several cycles.
If no cycle is selected, data selection will ignore cycles.

Under ``Stage(s)``, select in which stage or stages to find spindles. 
If no stage is selected, data selection will ignore stages.

Rejection
---------

``Minimum duration (sec)`` sets the minimum length of segments after artefact rejection and *before* concatenation, below which the segment is excluded.

``Exclude Poor signal epochs`` removes epochs marked as ``Poor`` signal.

``Exclude Artefact events`` removes signal concurrent with ``Artefact`` events *on all channels*.
For ``Artefact`` event marking, see notes_.

Concatenation
-------------

You can concatenate different stages, cycles, event types or channels.
Discontinuous signal will only be concatenated if the ``Concatenate discontinuous signal`` box is checked.
This holds for signal discontinuities introduced by artefact rejection.
Channel concatenation is only available if discontinuous signal is concatenated.
Concatenation is not available when the ``Lock to staging epochs`` option is selected.
Discontinuous signal concatenation is not available for ``by epoch`` chunking; if you would like this option to be implemented, please contact the authors.

Pre-processing
--------------

You may apply any or all of the following transformations to the signal before running the analyses on the right-hand side of the console: signal whitening, bandpass filtering and notch filtering.
The selected transformations are applied in the order displayed.

*Whitening*: Signal whitening removes the signal's 1/f background activity, leaving it with a flat, white noise-like frequency spectrum.
Signal whitening can help bring out spectral peaks in the signal, above and beyond background activity. 
In Wonambi's implementation, whitening is achieved by subtracting each signal sample by the previous sample.
To whiten the signal, check the ``Whiten`` checkbox in the Pre-processing box.

*Bandpass*: You may apply a variety of bandpass filter types with the drop-down menu, with options below for filter ``Order``, ``Lowcut`` and ``Highcut``.
You may instead choose to only apply a lowpass or highpass filter; in this case, ony include the ``Highcut`` or ``Lowcut``, respectively.

*Notch*: 
