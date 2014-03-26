



def Detect(QClass):
    """Description

    Attributes
    ----------
    parent : instance of QMainWindow
        The main window.
    attributes : type
        explanation

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.attributes = None  # public

        self.idx_XXX = []  # list of instances of the objects

        self.create_mywidget()

    def create_mywidget(self):
        """Create the widget with the elements that won't change."""
        lg.debug('Creating MyWidget widget')
        layout = QBoxLayout()

        layout.addWidget(QPushButton(''))
        self.setLayout(layout)


    def update_mywidget(self, parameters):
        """Update the attributes once the dataset has been read in memory.

        """
        lg.debug('Updating MyWidget widget')
        self.display_mywidget()

    def display_mywidget(self):
        lg.debug('Displaying MyWidget widget')
        """Update the widgets with the new information."""

    def do_more_things(self, input1):
        """Description

        Parameters
        ----------
        input1 : type
            Description.

        """
        pass
