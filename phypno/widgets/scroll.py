from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta
from numpy import squeeze
from PySide.QtCore import QSettings
from PySide.QtGui import (QGraphicsScene,
                          QGraphicsView,
                          QPainterPath,
                          QPen,
                          )
from ..trans import Montage, Filter

config = QSettings("phypno", "scroll_data")


class Trace(QPainterPath):

    def __init__(self, x, y):
        super().__init__()

        self.moveTo(x[0], y[0])
        for i_x, i_y in zip(x, y):
            self.lineTo(i_x, i_y)


class Scroll(QGraphicsView):
    """Main widget that contains the recordings to be plotted.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    ylimit : int
        positive height of the y-axis
    data : instance of phypno.DataTime
        instance containing the recordings.
    scene :

    chan_plot : list of instances of plotItem
        references to the plots for each channel.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.ylimit = config.value('ylimit')
        self.scene = None
        self.data = None
        self.chan_plot = None

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
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length

        all_chan = [chan for x in self.parent.channels.groups
                   for chan in x['chan_to_plot']]
        distance_traces = config.value('distance_traces')

        self.scene = QGraphicsScene(window_start,
                                    0,
                                    window_length,
                                    len(all_chan) * distance_traces +
                                    self.ylimit * 2)
        self.setScene(self.scene)
        data = self.data

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
                path = self.scene.addPath(Trace(time, squeeze(dat, axis=0)))
                path.setPen(QPen(one_grp['color']))
                path.setPos(0, distance_traces * row)
                row += 1
                chan_plot.append(path)

        self.chan_plot = chan_plot
        self.set_ylimit()

    def set_ylimit(self, new_ylimit=None):
        """Change the amplitude, you don't need to read in new data.

        Parameters
        ----------
        new_ylimit : float or int, optional
            the new amplitude of the plot

        """
        if new_ylimit is not None:
            self.ylimit = new_ylimit
        self.scale(1, 1/self.ylimit)

"""
    def add_datetime_on_x(self):
        Change the labels on the x-axis to include the current time.

        Notes
        -----
        This function creates a new function (tickStrings) which overrides the
        axis function in pyqtgraph.

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
"""
