from logging import getLogger
lg = getLogger(__name__)

from PySide.QtCore import Qt, QSettings
from PySide.QtGui import (QProgressBar,
                          QScrollBar,
                          QVBoxLayout,
                          QWidget,
                          )

config = QSettings("phypno", "scroll_data")


class Overview(QWidget):
    """Shows an overview of data, such as hypnogram and data in memory.

    Attributes
    ----------
    window_start : float
        start time of the window being plotted (in s).
    window_length : float
        length of the window being plotted (in s).

    Methods
    -------
    read_duration : reads full duration and update maximum.
    update_length : change length of the page step.
    update_position : if value changes, call scroll functions.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.window_start = config.value('window_start')
        self.window_length = config.value('window_length')

        self.scrollbar = QScrollBar()
        self.scrollbar.setOrientation(Qt.Orientation.Horizontal)
        self.scrollbar.sliderReleased.connect(self.update_position)

        self.progressbar = QProgressBar()

        layout = QVBoxLayout()
        layout.addWidget(self.scrollbar)
        layout.addWidget(self.progressbar)
        self.setLayout(layout)

        self.update_length(self.window_length)

    def read_duration(self):
        header = self.parent.info.dataset.header
        maximum = header['n_samples'] / header['s_freq']
        self.scrollbar.setMaximum(maximum - self.window_length)

    def update_length(self, new_length):
        self.window_length = new_length
        self.scrollbar.setPageStep(new_length)

    def update_position(self, new_position=None):
        if new_position is not None:
            self.window_start = new_position
            self.scrollbar.setValue(new_position)
        else:
            self.window_start = self.scrollbar.value()
        lg.info('Overview.update_position: read_data')
        self.parent.scroll.read_data()
        lg.info('Overview.update_position: plot_scroll')
        self.parent.scroll.plot_scroll()
