from logging import getLogger
lg = getLogger(__name__)

from numpy import log
from scipy.signal import welch

from PySide.QtGui import (QComboBox,
                          QVBoxLayout,
                          QWidget,
                          )
from visvis import use, plot, cla, gca


app = use('pyside')


class Spectrum(QWidget):
    """Plot the power spectrum for a specified channel.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        preferences = self.parent.preferences.values
        self.x_limit = preferences['spectrum/x_limit']
        self.y_limit = preferences['spectrum/y_limit']
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
        self.parent.traces.add_traces()

    def display_spectrum(self):
        cla()
        axis = gca()
        axis.position.x = 20
        axis.position.w = self.figure._widget.width() - axis.position.x
        axis.Draw()

        s_freq = int(self.parent.traces.data.s_freq)  # TODO
        f, Pxx = welch(self.data, fs=s_freq, nperseg=s_freq)
        plot(f, log(Pxx))
        axis.SetLimits(rangeX=self.x_limit, rangeY=self.y_limit)
        axis.showGrid = 1
