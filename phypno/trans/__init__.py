"""Package to transform the Data.

The modules in this package are classes (and maybe functions) that transform
the data into data again (all the classes defined in datatype.py). Do not
use this package to transform to other classes. If you want to transform to
basic elements, use the package "detect" for example.

"""
from .filter import Filter, Convolve
from .select import Select
from .frequency import Freq, TimeFreq
from .merge import Merge
from .math import Math
from .montage import Montage
from .reject import RejectBadChan
