from logging import getLogger
lg = getLogger(__name__)

from numpy import log, ceil, floor
from scipy.signal import welch
from PySide.QtCore import Qt
from PySide.QtGui import (QComboBox,
                          QVBoxLayout,
                          QWidget,
                          QGraphicsView,
                          QGraphicsScene,
                          QPen,
                          )

from phypno.widgets.utils import Path

TICK_SIZE = 20


class Spectrum(QWidget):
    """Plot the power spectrum for a specified channel.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    x_limit : tuple or list
        2 values specifying the limit on x-axis
    y_limit : tuple or list
        2 values specifying the limit on y-axis
    idx_chan : instance of QComboBox
        the element with the list of channel names.
    idx_fig : instance of QGraphicsView
        the view with the power spectrum
    scene : instance of QGraphicsScene
        the scene with GraphicsItems

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        preferences = self.parent.preferences.values
        self.x_limit = preferences['spectrum/x_limit']
        self.y_limit = preferences['spectrum/y_limit']

        self.idx_chan = None
        self.idx_fig = None
        self.scene = None

        self.create_spectrum()

    def create_spectrum(self):
        """Create empty scene for power spectrum."""

        self.idx_chan = QComboBox()
        self.idx_chan.activated.connect(self.display_spectrum)
        self.idx_fig = QGraphicsView(self)
        self.idx_fig.scale(1, -1)

        self.scene = QGraphicsScene(self.x_limit[0], self.y_limit[0],
                                    self.x_limit[1] - self.x_limit[0],
                                    self.y_limit[1] - self.y_limit[0])
        self.idx_fig.setScene(self.scene)

        layout = QVBoxLayout()
        layout.addWidget(self.idx_chan)
        layout.addWidget(self.idx_fig)
        self.setLayout(layout)

    def update_spectrum(self):
        """Add channel names to the combobox."""
        self.idx_chan.clear()
        for one_grp in self.parent.channels.groups:
            for one_chan in one_grp['chan_to_plot']:
                chan_name = one_chan + ' (' + one_grp['name'] + ')'
                self.idx_chan.addItem(chan_name)

        self.display_spectrum()

    def display_spectrum(self):
        """Make graphicsitem for spectrum figure."""
        chan_name = self.idx_chan.currentText()
        lg.info('Power spectrum for channel ' + chan_name)

        self.scene.clear()
        self.add_grid()

        data = self.parent.traces.data[chan_name]
        s_freq = int(self.parent.info.dataset.header['s_freq'])  # remove int
        f, Pxx = welch(data, fs=s_freq, nperseg=s_freq)

        freq_limit = (self.x_limit[0] <= f) & (f <= self.x_limit[1])
        self.scene.addPath(Path(f[freq_limit], log(Pxx[freq_limit])))

        self.resizeEvent(None)

    def add_grid(self):
        """Add axis and ticks to figure.

        Notes
        -----
        I know that visvis and pyqtgraphs can do this in much simpler way, but
        those packages create too large a padding around the figure and this is
        pretty fast.

        """
        # X-AXIS
        # x-bottom
        self.scene.addLine(self.x_limit[0], self.y_limit[0],
                           self.x_limit[0], self.y_limit[1])
        # at y = 0, dashed
        self.scene.addLine(self.x_limit[0], 0,
                           self.x_limit[1], 0, QPen(Qt.DashLine))
        # ticks on y-axis
        y_high = int(floor(self.y_limit[1]))
        y_low = int(ceil(self.y_limit[0]))
        x_length = (self.x_limit[1] - self.x_limit[0]) / TICK_SIZE
        for y in range(y_low, y_high):
            self.scene.addLine(self.x_limit[0], y,
                               self.x_limit[0] + x_length, y)
        # Y-AXIS
        # left axis
        self.scene.addLine(self.x_limit[0], self.y_limit[0],
                           self.x_limit[1], self.y_limit[0])
        # larger ticks on x-axis every 10 Hz
        x_high = int(floor(self.x_limit[1]))
        x_low = int(ceil(self.x_limit[0]))
        y_length = (self.y_limit[1] - self.y_limit[0]) / TICK_SIZE
        for x in range(x_low, x_high, 10):
            self.scene.addLine(x, self.y_limit[0],
                               x, self.y_limit[0] + y_length)
        # smaller ticks on x-axis every 10 Hz
        y_length = (self.y_limit[1] - self.y_limit[0]) / TICK_SIZE / 2
        for x in range(x_low, x_high, 5):
            self.scene.addLine(x, self.y_limit[0],
                               x, self.y_limit[0] + y_length)

    def resizeEvent(self, event):
        """Fit the whole scene in view.

        Parameters
        ----------
        event : instance of Qt.Event
            not important

        """
        self.idx_fig.fitInView(self.x_limit[0],
                               self.y_limit[0],
                               self.x_limit[1] - self.x_limit[0],
                               self.y_limit[1] - self.y_limit[0])
