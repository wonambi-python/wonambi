Analysis
========

Detect Events
-------------

Wonambi can automatically detect sleep spindles and slow waves in the signal.

To detect events, make sure you have first loaded a Montage and an Annotations File.
In your montage, create the desired channels for event detection. Note that filters set in the Channels tab are not retained for event detection.
Now, click on ``Analysis`` -> ``Detect`` and choose the desired event. This will open the detection dialog. 

Let us begin with the **spindle detection dialog**:

.. image:: images/notes_16_spindledialog.png

*Info*

Under ``Label``, enter the name of this event type, which will appear on the trace. You may choose an existing event type or create a new one. 
If you choose an existing event type, existing events of this type will be preserved.

Next, you will see ``Channel group`` and ``Channel(s)``. You may perform automatic detection on several channels at once, within a same group. 
Select the desired group from the drop-down menu, and select the channel(s). Select several channels by holding down the ``Ctrl`` key.

If you have delimited cycles (see notes_), the cycle indices will appear under ``Cycle(s)``. You may select one or several cycles.
If no cycle is selected, detection will ignore cycles.

Under ``Stage(s)``, select in which stage or stages to find spindles. 
If no stage is selected, detection will ignore stages.

.. NOTE::
   If you select neither a cycle nor a stage, detection will be carried out over the entire record, even wake!

*Parameters*

You may select among a number of spindle detection algorithms in the ``Method`` drop-down menu.
The parameter values will be updated to the values reported in the source literature.
These values remain fully customizable.
Note that not all method parameters are applicable to each method. 
In these cases, the method parameter is grayed out and marked ``N/A``.
For details about the implemented algorithms, consult the ``Help`` box, accessible at the bottom of the dialog.

*Options*

If you have marked events with event type "Artefact", you may check the ``Exclude Artefact events`` box to remove them from the detection signal.
Signal on all selected channels that is concurrent with an "Artefact" event on any channel will be excluded from detection, and the resulting signal segments will be concatenated.

If you selected several channels, you may choose to merge spindles detected in close proximity across channels with ``Merge events across channels``.
When selected, spindles on different channels that are separated by less than a certain delay will be merged onto the channel with the earliest onset spindle.
The delay is set with ``Minimum interval``, at the bottom of the dialog. If ``Minimum interval`` is set to zero, then only overlapping spindles will be merged.

The **slow wave detection dialog** is similar to the spindle detection dialog:

.. image:: images/notes_17_slowwavedialog.png

As in the spindle dialog, you can choose a slow wave detection algorithm from the ``Method`` drop-down menu, and the parameters will update with default values from the source literature.
Note that the ``AASM/Massimini_2004`` method is identical to the ``Massimini_2004`` algorithm, but with different default values for the method parameters.
For details about the implemented algorithms, consult the ``Help`` box, accessible at the bottom of the dialog.

The ``De-mean`` checkbox subtracts the mean of the detection signal for each channel.

The ``Invert detection`` checkbox allows you to "flip" the detection algorithm upside-down, so that instead of a "trough-then-peak" pattern, it will look for a "peak-then-trough" pattern.

For conceptual reasons, there is no option to merge events during slow wave detection.


Analysis console
----------------

Wonambi's analysis console allows the flexible selection of signal for a variety of analyses, including frequency domain analyses and phase-amplitude coupling (PAC).
Signal can be selected by event, epoch or longest run, and by channel, cycle and stage, with flexible concatenation options, and with artefacted signal excluded.

To open the dialog, click on ``Analysis`` -> ``Analysis console``.

.. image:: images/analysis_01_dialog.png

*File location*

Select the base name and location of the data files. The analysis console creates pickle (.p) and CSV files containing the raw analysis data.

.. NOTE::
   These data files can become quite large depending on the analysis.

*Chunking*

Different analyses require different lengths of signal, hence the chunking option. You may chunk by ``event``, ``epoch`` or ``longest run``.

Chunking ``by event`` gathers all events of the type(s) selected as individual segments.
If you wish to gather only the signal for the channel on which an event was marked, keep the ``Channel-specific`` box checked.
Alternatively, you may wish to gather signal concurrent to an event on all selected channels (channel selection is below).
In this case uncheck ``Channel-specific''.

Chunking ``by epoch`` gathers all relevant signal cut up into segments of equal durations.
To obtain the epochs as segmented by the Annotation file for sleep scoring, check ``Lock to staging epochs``.
Otherwise, you may select a different epoch length with ``Duration (sec)``. 
In this case, all relevant signal will be segmented at that duration, starting at the first sample of relevant signal.

Chunking ``by longest run`` gathers all relevant signal cut up into the longest continuous (uninterrupted) segments.
For instance, if in the sleep cycle selected there is a run of 10 minutes of REM, with another isolated 30s epoch of REM cut off from the rest, this option will return two segments, one 10 minutes long and one 30s long.

*Location*

Next, you will see ``Channel group`` and ``Channel(s)``. You may select signal from several channels within a same group. 

If you have delimited cycles (see notes_), the cycle indices will appear under ``Cycle(s)``. You may select one or several cycles.
If no cycle is selected, data selection will ignore cycles.

Under ``Stage(s)``, select in which stage or stages to find spindles. 
If no stage is selected, data selection will ignore stages.

*Rejection*

``Minimum duration (sec)`` sets the minimum length of segments after artefact rejection and before concatenation, below which the segment is excluded.

``Exclude Poor signal epochs`` removes epochs marked as ``Poor`` signal.

``Exclude Artefact events`` removes signal concurrent with ``Artefact`` events *on all channels*.
For ``Artefact`` event marking, see notes_.

*Concatenation*

Concatenation is available for ``by event`` and ``by longest run`` chunking.
You can concatenate different stages, cycles, event types or channels.
Discontinuous signal will only be concatenated if the ``Concatenate discontinuous signal`` box is checked.
This holds for signal discontinuities introduced by artefact rejection.


Merge events
------------

You may want to merge events outside of the automatic detection process.
For instance, you may want to merge spindles detected by different algorithms, or you my want to merge manually marked events with automatically detected ones.

To do this, click on ``Annotations`` -> ``Event`` -> ``Merge Events...`` to open the **merge events dialog**:

.. image:: images/notes_19_mergedialog.png

You may choose to merge events from one or several event types using the ``Event type(s)`` box. 
If you select several, you will be prompted to provide a label for the new event type created by the merger.
**Note that the selected event types will be deleted and replaced with the new event type.**

Events marked within a same channel will be merged if they are separated by up to a certain interval.
This interval is set with ``Minimum interval``.

In addition to merging events from within a same channel, you may choose to merge events marked on different channels.
To do so, check the ``Merge across channels`` box.
With this option checked, events on any channel separated by ``Minimum interval`` or less will be merged.

When events are merged across channels, only one channel keeps the event. 
That channel can either be the one that had the earliest onset event, or the longest event.
You can choose the channel selection rule with the ``Merge to...`` drop-down menu.

Analyze events
--------------

You can perform parametric analysis on any event type, whether the events were automatically detected, manually marked, or a mix of both.

Once you have marked all events of interest, click on ``Analysis`` -> ``Events...`` to open the **event analysis dialog**:

.. image:: images/notes_18_eventanalysisdialog.png

Consult the ``Help`` box for more details about the event analysis dialog.