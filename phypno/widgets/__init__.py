"""Package containing Qt widgets.

The program is organized in widgets:
  - info/Info : Information about the dataset.
  - channels/Channels : Allow user to choose channels, and filters.
  - overview/Overview : Show an overview of data.
  - traces/Traces : Show the traces of activity.
  - spectrum/Spectrum : Show the Welch's periodogram of one channel.
  - video/Video : Show the video of the recordings.

A module should start with:

from logging import getLogger
lg = getLogger(__name__)

then import packages that are in the Python library, additional packages (in
this order: numpy, scipy, PySide, visvis), relative imports (leave an empty
line between each group of imports).


  - widgets = one of the quadrants inside the main window
  - elements = qpushbutton, qlineedit etc
  - layout = grid layout, box layout, form layout

for-loop syntax: for one_label in labels

try to make at least one info or debug per function

A WIDGET SHOULD CONTAIN:

class MyWidget(QClass):
    \"""Description

    Attributes
    ----------
    parent : instance of QMainWindow
        The main window.
    attributes : type
        explanation

    \"""
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.attributes = None  # public

        self.idx_XXX = []  # list of instances of the objects

        self.create_mywidget()

    def create_mywidget(self):
        \"""Create the widget with the elements that won't change.\"""
        lg.debug('Creating MyWidget widget')
        layout = QBoxLayout()

        layout.addWidget(QPushButton(''))
        self.setLayout(layout)


    def update_mywidget(self, parameters):
        \"""Update the attributes once the dataset has been read in memory.

        \"""
        lg.debug('Updating MyWidget widget')
        self.display_mywidget()

    def display_mywidget(self):
        \"""Update the widgets with the new information.\"""
        lg.debug('Displaying MyWidget widget')

    def do_more_things(self, input1):
        \"""Description

        Parameters
        ----------
        input1 : type
            Description.

        \"""
        pass

I don't know if the widget layout should be created in __init__ or in
display_mywidget. It probably depends: elements of the widget that can be
visualized before the dataset is loaded should go in __init__, the other ones
in display_mywidget. But it's important that all the elements that are
attributes to self are defined in __init__ even if empty.

"""
from .preferences import Preferences
from .channels import Channels
from .info import Info
from .overview import Overview
from .notes import Bookmarks, Events, Stages
from .traces import Traces
from .detect import Detect
from .spectrum import Spectrum
from .utils import DockWidget
from .video import Video
