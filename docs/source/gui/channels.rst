.. _channels:

Plot Channels
=============

You can create multiple channel groups.
Each channel group has its own reference, and filter settings.
You can also choose a specific color for each group.

.. image:: images/channels_01_onegroup.png

By clicking on ``new`` you can create a second channel group, f.e. called ``eog``.

.. image:: images/channels_02_eog.png

For each channel group, you can modify settings for the high-pass filter:

.. image:: images/channels_03_hp.png

and low-pass filter:

.. image:: images/channels_04_lp.png

.. NOTE::
   ``0`` means that the (high-pass or low-pass) filter won't be applied.
   

You can also modify the scaling, f.e. if the amplitude of a channel group is too small, you can double the size:

.. image:: images/channels_05_scale.png

For each channel group, you can specify how to reference the channels, on-line. You can select the individual channels from the columns on the right:

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
If you're happy with a selection of channels (organized in channel groups, including filter settings and references), you can click on ``Save Channel Montage``:

.. image:: images/channels_12_save_chan.png

and then you'll be asked to save the current montage on a file on disk.

.. NOTE::
   The channel montage is stored in the ``.json`` format, which is actually a text file, so it's easy to read and modify if necessary.

Load Montage
------------
Once you reopen the same dataset, you can click on ``Load Channel Montage``:

.. image:: images/channels_13_load_chan.png

and then the previously saved channel groups will be shown directly:

.. image:: images/channels_14_loaded.png

.. NOTE::
   You can use the same file for the channel montage as long as the labels are the same.

