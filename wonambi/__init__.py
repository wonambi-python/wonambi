"""
Phypno main module
"""
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'VERSION')) as f:
    __version__ = f.read().strip()

from .dataset import Dataset
from .datatype import Data, ChanTime, ChanFreq, ChanTimeFreq
from .graphoelement import Graphoelement
from .bin.scroll_data import MainWindow as Wonambi
