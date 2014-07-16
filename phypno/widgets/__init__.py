"""Package containing Qt widgets.

The program is organized in widgets:
  - info/Info : Information about the dataset.
  - channels/Channels : Allow user to choose channels, and filters.
  - overview/Overview : Show an overview of data.
  - notes/Notes : Show annotations, such as markers and sleep staging
  - traces/Traces : Show the traces of activity.
  - spectrum/Spectrum : Show the Welch's periodogram of one channel.
  - video/Video : Show the video of the recordings.

A module should start with:

from logging import getLogger
lg = getLogger(__name__)

then import packages that are in the Python library, additional packages (in
this order: numpy, scipy, PyQt4, visvis), relative imports (leave an empty
line between each group of imports).


  - widgets = one of the quadrants inside the main window
  - elements = qpushbutton, qlineedit etc
  - layout = grid layout, box layout, form layout

"""
