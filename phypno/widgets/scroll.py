from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta
from numpy import squeeze, floor, ceil
from PySide.QtCore import QSettings, QPointF
from PySide.QtGui import (QBrush,
                          QGraphicsScene,
                          QGraphicsSimpleTextItem,
                          QGraphicsView,
                          QPainterPath,
                          QPen,
                          )

from ..trans import Montage, Filter
from .utils import Trace

config = QSettings("phypno", "scroll_data")


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
        self.y_scale = config.value('y_scale')
        self.y_dist = config.value('y_dist')
        self.y_scrollbar_value = 0
        self.scene = None
        self.data = None
        self.all_chan = []
        self.all_label = []
        self.all_time = []
        self.all_bookmark = []

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
        self.display_scroll(data)
        self.parent.overview.more_download(window_start, window_end)

    def create_labels(self):
        """Create the channel labels, but don't plot them yet."""

        self.all_label = []
        for one_grp in self.parent.channels.groups:
            for one_label in one_grp['chan_to_plot']:
                item = QGraphicsSimpleTextItem(one_label)
                item.setBrush(QBrush(one_grp['color']))
                self.all_label.append(item)

    def create_time(self, times):
        """Create the time labels, but don't plot them yet.

        Notes
        -----
        Not very robust, because it uses seconds as integers.

        """
        start_time = self.parent.info.dataset.header['start_time']

        min_time = int(floor(min(times)))
        max_time = int(ceil(max(times)))
        n_time_labels = config.value('n_time_labels')
        step = int((max_time - min_time) / n_time_labels)

        self.all_time = []
        self.all_time_pos = []
        for one_time in range(min_time, max_time, step):
            x_label = (start_time +
                       timedelta(seconds=one_time)).strftime('%H:%M:%S')
            self.all_time.append(QGraphicsSimpleTextItem(x_label))
            self.all_time_pos.append(QPointF(one_time,
                                             len(self.all_label) *
                                             self.y_dist))

    def display_scroll(self, data=None):
        """Display the recordings."""
        if data is None:
            data = self.data

        if self.scene is not None:
            self.y_scrollbar_value = self.verticalScrollBar().value()
            self.scene.clear()

        self.create_labels()
        self.create_time(data.time)

        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length

        label_width = config.value('label_width')
        time_height = max([x.boundingRect().height() for x in self.all_time])

        self.scene = QGraphicsScene(window_start - label_width,
                                    0,
                                    window_length + label_width,
                                    len(self.all_label) * self.y_dist +
                                    time_height)
        self.setScene(self.scene)
        self.add_labels()
        self.add_time()
        self.add_data(data)
        self.set_y_scale()
        self.resizeEvent(None)
        self.verticalScrollBar().setValue(self.y_scrollbar_value)

    def add_labels(self):
        """Add channel labels on the left."""
        window_start = self.parent.overview.window_start

        label_width = config.value('label_width')

        for row, one_label_item in enumerate(self.all_label):
            self.scene.addItem(one_label_item)
            one_label_item.setPos(window_start - label_width,
                                  self.y_dist * row + self.y_dist / 2)

    def add_time(self):
        for text, pos in zip(self.all_time, self.all_time_pos):
            self.scene.addItem(text)
            text.setPos(pos)

    def add_data(self, data=None):
        if data is None:
            data = self.data
        self.y_dist = self.y_dist

        self.all_chan = []  # does not delete previous channels
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
                dat = squeeze(dat, axis=0)
                path = self.scene.addPath(Trace(time,
                                                dat * one_grp['scale']))
                path.setPen(QPen(one_grp['color']))
                path.setPos(0, self.y_dist * row + self.y_dist / 2)
                self.all_chan.append(path)
                row += 1
                if self.parent.spectrum.channel is not None:
                    if chan == self.parent.spectrum.channel:
                        self.parent.spectrum.data = dat
                        self.parent.spectrum.display_spectrum()

        self.set_y_scale()
        if self.parent.bookmarks.bookmarks is not None:
            self.add_bookmarks()

    def set_y_scale(self, new_y_scale=None):
        """Change the amplitude, you don't need to read in new data.

        Parameters
        ----------
        new_y_scale : float or int, optional
            the new scale for the y-axis.

        """
        if new_y_scale is not None:
            self.y_scale = new_y_scale
        for chan in self.all_chan:
            chan.resetTransform()
            chan.scale(1, self.y_scale)

    def resizeEvent(self, event):
        view_width = self.width()
        if self.scene is not None:
            scene_width = self.scene.sceneRect().width()
            self.resetTransform()
            scale_value = view_width / (scene_width + 1)
            self.scale(scale_value, 1)

            for text in self.all_time:
                text.resetTransform()
                text.scale(1 / scale_value, 1)
            for text in self.all_label:
                text.resetTransform()
                text.scale(1 / scale_value, 1)

    def add_bookmarks(self):
        """Add bookmarks on top of first plot."""
        bookmarks = self.parent.bookmarks.bookmarks
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length
        window_end = window_start + window_length

        self.all_bookmark = []
        for bm in bookmarks:
            if window_start < bm['time'] < window_end:
                item = QGraphicsSimpleTextItem(bm['name'])
                item.setPos(bm['time'], 0)
                self.all_bookmark.append(item)
