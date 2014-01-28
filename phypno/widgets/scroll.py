from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta
from numpy import squeeze
from PySide.QtCore import QSettings
from PySide.QtGui import (QGridLayout,
                          QPen,
                          QWidget,
                          )
from pyqtgraph import PlotWidget, TextItem
from pyqtgraph.graphicsItems.AxisItem import AxisItem
from ..trans import Montage, Filter

config = QSettings("phypno", "scroll_data")


class Scroll(QWidget):
    """Main widget that contains the recordings to be plotted.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    ylimit : int
        positive height of the y-axis
    data : instance of phypno.DataTime
        instance containing the recordings.
    layout : instance of QGridLayout
        layout of the channels
    chan_plot : list of instances of plotItem
        references to the plots for each channel.

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

    def update_scroll(self):
        """Read and update the data to plot."""
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

    def display_scroll(self):
        """Display the recordings."""
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
        self.add_bookmarks()

    def set_ylimit(self, new_ylimit=None):
        """Change the amplitude, you don't need to read in new data.

        Parameters
        ----------
        new_ylimit : float or int, optional
            the new amplitude of the plot

        """
        if new_ylimit is not None:
            self.ylimit = new_ylimit
        chan_plot = self.chan_plot
        for single_chan_plot in chan_plot:
            single_chan_plot.plotItem.setYRange(-1 * self.ylimit,
                                                self.ylimit)

    def add_bookmarks(self):
        """Add bookmarks on top of first plot."""
        bookmarks = self.parent.bookmarks.bookmarks
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length
        window_end = window_start + window_length
        for bm in bookmarks:
            if window_start < bm['time'] < window_end:
                self.text = TextItem(bm['name'],
                                anchor=(0, 0))  # TODO: not correct
                self.chan_plot[0].addItem(self.text)

    def add_datetime_on_x(self):
        """Change the labels on the x-axis to include the current time.

        Notes
        -----
        This function creates a new function (tickStrings) which overrides the
        axis function in pyqtgraph.

        """
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

