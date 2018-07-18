"""Package to transform the Data.

The modules in this package are classes (and maybe functions) that transform
the data into data again (all the classes defined in datatype.py). Do not
use this package to transform to other classes. If you want to transform to
basic elements, use the package "detect" for example.

"""
from .filter import filter_, convolve
from .select import (select, resample, get_times, _select_channels, fetch, 
                     Segments)
from .frequency import frequency, timefrequency, band_power
from .merge import concatenate
from .math import math, get_descriptives, event_params, export_event_params
from .montage import montage
from .peaks import peaks
from .reject import rejectbadchan, remove_artf_evts

