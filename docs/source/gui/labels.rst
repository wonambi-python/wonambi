.. _edit-labels:

Edit Labels
===========

Sometimes, the labels in the recordings are not correct (f.e. typos or some channels were changed) or might be completely uninformative (f.e. BCI2000 does not have channel labels).
From the `labels` panel, you can edit the labels and load from a list of labels.

.. image:: images/labels_01_table.png

The column on the left shows the current (original) labels while the column on the right can be edited to change the labels.
Select one label from the right-hand column and write the name of the label:

.. image:: images/labels_02_newlabel.png

It's crucial that the channels have unique labels, so if you use the same label twice, you cannot continue (the duplicated labels are highlighted in red):

.. image:: images/labels_03_duplicate.png

Fix the label before proceeding:

.. image:: images/labels_04_correct.png

Then, click on `apply` to propagate the new labels to the whole app.

.. WARNING::
   Clicking `apply` will reset the traces and channel groups, because they are based on the labels.

You then need to create the channel groups and plot the signal.
Note the updated labels:

.. image:: images/labels_05_traces.png


