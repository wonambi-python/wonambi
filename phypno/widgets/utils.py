from logging import getLogger, INFO
lg = getLogger(__name__)
lg.setLevel(INFO)

from PySide.QtGui import QDockWidget, QPainterPath


class DockWidget(QDockWidget):
    """Simple DockWidget, that, when closes, changes the check on the menu.

    """
    def __init__(self, parent, name, subwidget, area):
        super().__init__(name, parent)
        self.parent = parent
        self.name = name
        self.setAllowedAreas(area)
        self.setWidget(subwidget)

    def closeEvent(self, event):
        """Override the function, so that it closes and changes the check in
        the menu.

        Parameters
        ----------
        event : unknown
            we don't care.

        """
        self.parent.toggle_menu_window(self.name, self)


class Trace(QPainterPath):

    def __init__(self, x, y):
        super().__init__()

        self.moveTo(x[0], y[0])
        for i_x, i_y in zip(x, y):
            self.lineTo(i_x, i_y)
