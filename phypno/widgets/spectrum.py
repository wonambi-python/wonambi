
from numpy import log
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

from visvis import use, plot, cla, gca

config = QSettings("phypno", "scroll_data")

app = use('pyside')


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
        Figure = app.GetFigureClass()
        self.figure = Figure(self)

        layout = QVBoxLayout()
        layout.addWidget(self.combobox)
        layout.addWidget(self.figure._widget)
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
        cla()
        axis = gca()
        axis.position.x = 20
        axis.position.w = self.figure._widget.width() - axis.position.x
        axis.Draw()

        s_freq = int(self.parent.scroll.data.s_freq)  # TODO
        f, Pxx = welch(self.data, fs=s_freq, nperseg=s_freq)
        plot(f, log(Pxx))
        axis.SetLimits(rangeX=self.x_lim, rangeY=self.y_lim)
        axis.showGrid = 1
