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

Under ``Stage(s)``, select in which stage or stages to find spindles (``Ctrl`` + click to pick more than one). 
If no stage is selected, detection will be performed over the entire record.

If you selected several channels, you may choose to merge spindles detected in close proximity across channels with ``Merge events across channels``.
When selected, spindles on different channels that are separated by less than a certain delay will be merged onto the channel with the earliest onset spindle.
The delay is set with ``Minimum interval``, at the bottom of the dialog. If ``Minimum interval`` is set to zero, then only overlapping spindles will be merged.

*General parameters*

Set the minimum and maximum frequency of the spindles with ``Lowcut`` and ``Highcut``, respectively.

Set the ``Minimum duration`` and ``Maximum duration`` of the spindles, in seconds.

*Method parameters*

You may select among a number of spindle detection algorithms in the ``Method`` drop-down menu.
The values of the method parameters will be updated to the values reported in the source literature.
These values remain fully customizable.
Note that not all method parameters are applicable to each method. 
In these cases, the method parameter is grayed out and marked ``N/A``.
For details about the implemented algorithms, consult the ``Help`` box, accessible at the bottom of the dialog.

The **slow wave detection dialog** is similar to the spindle detection dialog:

.. image:: images/notes_17_slowwavedialog.png

For conceptual reasons, there is no option to merge events during slow wave detection.

Instead of a merging checkbox, you will see the ``Invert detection`` checkbox.
This option allows you to "flip" the detection algorithm upside-down, so that instead of a "trough-then-peak" pattern, it will look for a "peak-then-trough" pattern.

As in the spindle dialog, you can choose a slow wave detection algorithm from the ``Method`` drop-down menu, and the Method parameters will update with default values from the source literature.
Note that the ``AASM/Massimini_2004`` method is identical to the ``Massimini_2004`` algorithm, but with different default values for the method parameters.
For details about the implemented algorithms, consult the ``Help`` box, accessible at the bottom of the dialog.

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