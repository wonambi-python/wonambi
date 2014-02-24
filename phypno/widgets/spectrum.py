from logging import getLogger
lg = getLogger(__name__)

from numpy import log
from scipy.signal import welch
from PySide.QtGui import (QComboBox,
                          QVBoxLayout,
                          QWidget,
                          QGraphicsView,
                          QGraphicsScene,
                          )

from phypno.widgets.utils import Path


class Spectrum(QWidget):
    """Plot the power spectrum for a specified channel.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        preferences = self.parent.preferences.values
        self.x_limit = preferences['spectrum/x_limit']
        self.y_limit = preferences['spectrum/y_limit']
        self.freq = None
        self.power = None

        self.idx_chan = None
        self.idx_fig = None

        self.create_spectrum()

    def create_spectrum(self):

        self.idx_chan = QComboBox()
        self.idx_chan.currentIndexChanged.connect(self.display_spectrum)
        self.idx_fig = QGraphicsView(self)
        self.idx_fig.scale(1, -1)

        self.scene = QGraphicsScene(self.x_limit[0], self.y_limit[1],
                                    self.x_limit[1] - self.x_limit[0],
                                    self.y_limit[1] - self.y_limit[0])
        self.idx_fig.setScene(self.scene)

        layout = QVBoxLayout()
        layout.addWidget(self.idx_chan)
        layout.addWidget(self.idx_fig)
        self.setLayout(layout)

    def update_spectrum(self):
        """Get value of the channel from scroll.

        """
        self.idx_chan.clear()
        groups = self.parent.channels.groups
        for one_grp in self.parent.channels.groups:
            for one_chan in one_grp['chan_to_plot']:
                chan_name = one_chan + ' (' + one_grp['name'] + ')'
                self.idx_chan.addItem(chan_name)

        self.display_spectrum()

    def display_spectrum(self):
        chan_name = self.idx_chan.currentText()
        data = self.parent.traces.data[chan_name]
        s_freq = int(self.parent.info.dataset.header['s_freq'])

        f, Pxx = welch(data, fs=s_freq, nperseg=s_freq)

        self.scene.addPath(Path(self.x_limit, [self.y_limit[0], self.y_limit[0]]))
        self.scene.addPath(Path([self.x_limit[0], self.x_limit[0]],
                                self.y_limit))
        self.scene.addPath(Path(f, log(Pxx)))

    def resizeEvent(self, event):


