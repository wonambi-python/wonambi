from logging import getLogger, INFO
lg = getLogger(__name__)
lg.setLevel(INFO)

from numpy import linspace
from PySide.QtCore import QSettings, Signal, QThread
from PySide.QtGui import QDockWidget

config = QSettings("phypno", "scroll_data")


class DownloadData(QThread):
    """Creates a new thread, that reads all the data consecutively.

    Notes
    -----
    TODO: restart from a new position, when you move the cursor.
    TODO: implement this the clean way of QThread

    """
    one_more_interval = Signal(float, float)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def run(self):
        """Override the function to do the hard-lifting.

        Notes
        -----
        TODO: be more careful about begtime and endtime.

        """
        dataset = self.parent.info.dataset
        steps = linspace(0, self.parent.overview.maximum)  # config.value('read_intervals')

        one_chan = dataset.header['chan_name'][0]
        for begtime, endtime in zip(steps[:-1], steps[1:]):
            dataset.read_data(chan=[one_chan],
                              begtime=begtime,
                              endtime=endtime)
            self.one_more_interval.emit(begtime, endtime)


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
