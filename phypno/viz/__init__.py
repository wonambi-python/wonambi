"""Module to visualize things in:
  - 1d (plot_1d.py), such as:
      - time-series
  - things in 2d (plot_2d.py), such as:
      - topoplot
      - time-frequency plots
      - mri images
  - things in 3d (plot_3d.py), such as:
      - surfaces (meshes)
      - channels

This module should contain only functions.
Inputs to the function should be objects.

We might include these functions as methods to classes in the future, but it
might complicate the code, instead of making it more clear.

"""

from .plot_1d import Viz1
from .plot_2d import Viz2
from .plot_3d import Viz3
