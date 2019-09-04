.. _channels:

Plot Channels
=============

You can create multiple channel groups.
Each channel group has its own reference, and filter settings.
You can also choose a specific color for each group.
Active channels are selected in the left-hand column.

.. image:: images/channels_01_onegroup.png


* If you click on a single item, the selection is cleared and the new item selected. 
* Multiple consecutive items can be selected by dragging the mouse over them.
* If you press the Ctrl key when clicking on an item, the clicked item gets toggled and all other items are left untouched. In this way you can add one single channel to the selection or remove one single channel from the selection.
* If you press the Shift key while clicking on an item, all items between the current item and the clicked item are selected or unselected, depending on the state of the clicked item. 

By clicking on ``New`` you can create a second channel group, e.g. called `eog`.

.. image:: images/channels_02_eog.png

For each channel group, you can modify settings for the high-pass filter:

.. image:: images/channels_03_hp.png

and low-pass filter:

.. image:: images/channels_04_lp.png

.. NOTE::
   ``0.0 Hz`` means that the (high-pass, low-pass or notch) filter won't be applied.

You can also apply the notch filter. Depending on your power line frequency, enter `60` (mostly North and Central America) or `50` (rest of the world).

.. image:: images/channels_05_notch.png

.. NOTE::
   Because the frequency for the notch filter depends on the country you're in, you should probably enter the default value for the notch filter in the Settings.

You can also modify the scaling, e.g. if the amplitude of a channel group is too small, you can double the size:

.. image:: images/channels_05_scale.png

You can remove the mean for each channel group individually. 
Removing the mean might be useful if your data has a constant offset.

.. image:: images/channels_05_demean.png

For each channel group, you can specify how to reference the channels, on-line. You can select the individual channels from the right-hand column. If you select more than one reference channel, their average will be taken as the reference:

.. image:: images/channels_06_ref.png

If you select many channels to plot on the left side, you can click on ``average`` and it will select all chosen channels as reference (this is the average reference):

.. image:: images/channels_07_avgref.png

Finally, remember to click ``Apply`` so that the changes are applied:

.. image:: images/channels_08_apply.png

You can also change the color of a channel group, by clicking on ``Color``:

.. image:: images/channels_09_color.png

The channels in that group will change color, in this case, red:

.. image:: images/channels_10_colored.png

Finally, you can also delete a channel group, by clicking on ``Delete``:

.. image:: images/channels_11_delete.png

Save Montage
------------
If you're happy with a selection of channels (organized in channel groups, including filter settings and references), you can click on ``Save Montage``:

.. image:: images/channels_12_save_chan.png

and you'll be asked to save the current montage to a file on disk.

.. NOTE::
   The channel montage is stored in the ``.json`` format, which is actually a text file, so it's easy to read and modify if necessary.

Load Montage
------------
Once you reopen the same dataset, you can click on ``Load Montage``:

.. image:: images/channels_13_load_chan.png

then, the previously saved channel groups will be shown directly:

.. image:: images/channels_14_loaded.png

.. NOTE::
   You can reuse the same channel montage file as long as the channel labels are the same.

