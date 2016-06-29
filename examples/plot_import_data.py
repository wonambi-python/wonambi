# -*- coding: utf-8 -*-
"""
============
Reading Data
============

You can import data from a variety of native formats, such as EDF, MNE-FIFF,
EGI MFF, and Matlab formats, such as FieldTrip.

One of the main principles is that you hardly ever want to read the whole
data recording in memory. To accomplish this, there are two major classes:
the Dataset, which contains information regarding the dataset, and Data, which
contains the actual data.
"""


##
# When you want to read some recordings, you first need to define a Dataset:

from phypno import Dataset
d = Dataset('/path/to/dataset')

