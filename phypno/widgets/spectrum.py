
from scipy.signal import welch

from PySide.QtCore import QSettings
from PySide.QtGui import (QComboBox,
                          QGraphicsScene,
                          QVBoxLayout,
                          QGraphicsView,
                          QPainterPath,
                          QPen,
                          QWidget,
                          )

from .utils import Trace

config = QSettings("phypno", "scroll_data")


class Spectrum(QWidget):
    """Plot the power spectrum for a specified channel.

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.x_lim = config.value('spectrum_x_lim')
        self.y_lim = config.value('spectrum_y_lim')
        self.channel = None
        self.data = None

        self.combobox = QComboBox()
        self.combobox.currentIndexChanged.connect(self.load_channel)
        self.view = QGraphicsView()

        layout = QVBoxLayout()
        layout.addWidget(self.combobox)
        layout.addWidget(self.view)
        self.setLayout(layout)

    def update_spectrum(self):
        """Get value of the channel from scroll.

        """
        self.combobox.clear()
        groups = self.parent.channels.groups
        all_chan = [item for x in groups for item in x['chan_to_plot']]
        for one_chan in all_chan:
            self.combobox.addItem(one_chan)

        #TODO: track this function: when changing groups, it plots the traces twice
        self.load_channel()

    def load_channel(self):
        self.channel = self.combobox.currentText()
        self.parent.scroll.add_data()

    def display_spectrum(self):
        # s_freq = self.parent.scroll.data.s_freq
        # f, Pxx = welch(self.data, fs=s_freq, nperseg=s_freq)

        scene = QGraphicsScene(self.x_lim[0], self.y_lim[1],
                               self.x_lim[1] - self.x_lim[0],
                               self.x_lim[0] - self.x_lim[1])

        self.view.resetTransform()
        self.view.scale(1, -1)
        self.view.setScene(scene)
        scene.addPath(Trace([0, 70], [0, 0]))
        scene.addPath(Trace([0, 70], [-5, 5]))
        scene.addPath(Trace([0, 70], [0, 5]))
        scene.addPath(Trace([0, 70], [0, 15]))

