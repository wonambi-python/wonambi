"""Package containing Qt widgets.

A widget should contain:
  - __init__(self, parent), where parent is the QMainWindow. It calls super
    first, then it initializes ALL the attributes (even if they are None or [])
    then it possibly creates empty sub-widgets (this preferably not).
  - update_XXX(self, parameters), which updates the attributes once the dataset
    has been read in memory. This function then calls display_XXX
  - display_XXX(self), which updates the widgets with the new information.
  - additional methods.

"""
from .channels import Channels
from .info import Info
from .overview import Overview
from .notes import Bookmarks, Events, Stages
from .scroll import Scroll
from .utils import DockWidget
from .video import Video
