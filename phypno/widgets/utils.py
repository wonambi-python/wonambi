from logging import getLogger, INFO
lg = getLogger(__name__)
lg.setLevel(INFO)

from numpy import floor
from PySide.QtCore import QSettings, QThread, Signal
from PySide.QtGui import QDockWidget

config = QSettings("phypno", "scroll_data")


class DownloadData(QThread):
    # remember to close it
    one_more_interval = Signal(int)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        dataset = self.parent.info.dataset
        progressbar = self.parent.overview.progressbar
        total_dur = dataset.header['n_samples'] / dataset.header['s_freq']
        maximum = int(floor(total_dur / config.value('read_intervals')))
        progressbar.setMaximum(maximum - 1)

        self.maximum = maximum

    def run(self):
        dataset = self.parent.info.dataset
        one_chan = dataset.header['chan_name'][0]
        for i in range(0, self.maximum):
            dataset.read_data(chan=[one_chan],
                              begtime=i * config.value('read_intervals'),
                              endtime=i * config.value('read_intervals') + 1)
            self.one_more_interval.emit(i)

        self.exec_()


class DockWidget(QDockWidget):
    def __init__(self, parent, name, subwidget, area):
        super().__init__(name, parent)
        self.parent = parent
        self.name = name
        self.setAllowedAreas(area)
        self.setWidget(subwidget)

    def closeEvent(self, event):
        self.parent.toggle_menu_window(self.name, self)
