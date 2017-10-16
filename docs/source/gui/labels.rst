.. _edit-labels:

Edit Labels
===========

Sometimes, the labels in the recordings are not correct (e.g. typos or some channels were changed) or might be completely uninformative (e.g. BCI2000 does not have channel labels).
From the `labels` panel, you can edit the labels and load from a list of labels.

.. image:: images/labels_01_table.png

The column on the left shows the current (original) labels while the column on the right can be edited to change the labels.
Select one label from the right-hand column and write the name of the label:

.. image:: images/labels_02_newlabel.png

It's crucial that the channels have unique labels, so if you use the same label twice, you cannot continue (the duplicated labels are highlighted in red):

.. image:: images/labels_03_duplicate.png

Fix the label before proceeding:

.. image:: images/labels_04_correct.png

Then, click on ``Apply`` to propagate the new labels to the whole app.

.. WARNING::
   Clicking ``Apply`` will reset the traces and channel groups, because they are based on the labels.

You then need to create the channel groups and plot the signal.
Note the updated labels:

.. image:: images/labels_05_traces.png

Load Labels from File
---------------------

You can also load the list of labels from a file on a disk. 
It should be a simple text file, where the labels are separated by either commas (comma-separated values), tabs, semicolon, new lines.
e.g.::

    newchan01, newchan02, newchan03,, newchan05

Note the double commas, meaning that channel 4 won't be modified.

To import the labels, click on ``Load``:

.. image:: images/labels_06_load_button.png

And after selecting the file, you should see the changes in the list on the right.
You can modify the labels further, and click ``Apply`` to make the changes effective.

.. image:: images/labels_07_loaded.png
