"""CONVENTIONS:
  - when writing log.info or log.debug, use the syntax:
  'the value of widget ' + widget_name + ' is ' + one_value
  if they are all strings. If one of them is not a string, use format

DEPENDENCY:
  For the whole package: numpy, scipy
  For module attr.anat: nibabel (optional)
  For module viz: visvis
  For module widgets: pyside

"""

from .dataset import Dataset
from .datatype import Data, ChanTime, ChanFreq, ChanTimeFreq
