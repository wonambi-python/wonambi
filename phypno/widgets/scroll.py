from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta
from numpy import squeeze
from PySide.QtCore import QSettings
from PySide.QtGui import (QGridLayout,
                          QPen,
                          QWidget,
                          )
from pyqtgraph import PlotWidget
from pyqtgraph.graphicsItems.AxisItem import AxisItem
from ..trans import Montage, Filter

config = QSettings("phypno", "scroll_data")


class Scroll(QWidget):
    """
        read_data : read data
    plot_scroll : plot data to scroll
    set_ylimit : set y limits for scroll data
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.ylimit = config.value('ylimit')
        self.data = None
        self.chan_plot = None

        layout = QGridLayout()
        layout.setVerticalSpacing(0)

        self.setLayout(layout)
        self.layout = layout

    def read_data(self):
        window_start = self.parent.overview.window_start
        window_end = window_start + self.parent.overview.window_length
        dataset = self.parent.info.dataset

        chan_to_read = []
        for one_grp in self.parent.channels.groups:
            chan_to_read.extend(one_grp['chan_to_plot'] +
                                one_grp['ref_chan'])
        data = dataset.read_data(chan=chan_to_read,
                                 begtime=window_start,
                                 endtime=window_end)
        self.data = data

    def plot_scroll(self):
        data = self.data
        layout = self.layout

        chan_plot = []
        row = 0
        for one_grp in self.parent.channels.groups:
            mont = Montage(ref_chan=one_grp['ref_chan'])
            data1 = mont(data)
            if one_grp['filter']['low_cut'] is not None:
                hpfilt = Filter(low_cut=one_grp['filter']['low_cut'],
                                s_freq=data.s_freq)
                data1 = hpfilt(data1)
            if one_grp['filter']['high_cut'] is not None:
                lpfilt = Filter(high_cut=one_grp['filter']['high_cut'],
                                s_freq=data.s_freq)
                data1 = lpfilt(data1)

            for chan in one_grp['chan_to_plot']:
                dat, time = data1(chan=[chan])
                chan_plot.append(PlotWidget())
                chan_plot[row].plotItem.plot(time, squeeze(dat, axis=0),
                                             pen=QPen(one_grp['color']))
                chan_plot[row].plotItem.setLabels(left=chan)
                chan_plot[row].plotItem.showAxis('bottom', False)
                chan_plot[row].plotItem.setXRange(time[0], time[-1])
                layout.addWidget(chan_plot[row], row, 0)
                row += 1

        chan_plot[row - 1].plotItem.showAxis('bottom', True)
        self.chan_plot = chan_plot
        self.set_ylimit()

    def set_ylimit(self, new_ylimit=None):
        if new_ylimit is not None:
            self.ylimit = new_ylimit
        chan_plot = self.chan_plot
        for single_chan_plot in chan_plot:
            single_chan_plot.plotItem.setYRange(-1 * self.ylimit,
                                                self.ylimit)

    def add_datetime_on_x(self):
        start_time = self.parent.info.dataset.header['start_time']

        def tickStrings(axis, values, c, d):
            if axis.orientation == 'bottom':
                strings = []
                for v in values:
                    strings.append((start_time +
                                    timedelta(seconds=v)).strftime('%H:%M:%S'))
            else:
                strings = [str(x) for x in values]
            return strings

        AxisItem.tickStrings = tickStrings
