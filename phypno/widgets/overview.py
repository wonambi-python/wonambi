from logging import getLogger
lg = getLogger(__name__)

from PySide.QtCore import Qt, QSettings
from PySide.QtGui import (QProgressBar,
                          QScrollBar,
                          QVBoxLayout,
                          QWidget,
                          )

config = QSettings('phypno', 'scroll_data')


class Overview(QWidget):
    """Show an overview of data, such as hypnogram and data in memory.

    Attributes
    ----------
    window_start : float
        start time of the window being plotted (in s).
    window_length : float
        length of the window being plotted (in s).

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.window_start = config.value('window_start')
        self.window_length = config.value('window_page_length')

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
        """Read full duration and update maximum.

        """
        header = self.parent.info.dataset.header
        maximum = header['n_samples'] / header['s_freq']
        self.scrollbar.setMaximum(maximum - self.window_length)

    def update_length(self, new_length):
        """Change length of the page step.

        """
        self.window_length = new_length
        self.scrollbar.setPageStep(new_length)

    def update_position(self, new_position=None):
        """If value changes, call scroll functions.

        """
        if new_position is not None:
            self.window_start = new_position
            self.scrollbar.setValue(new_position)
        else:
            self.window_start = self.scrollbar.value()
        self.parent.scroll.update_scroll()
        self.parent.scroll.display_scroll()
