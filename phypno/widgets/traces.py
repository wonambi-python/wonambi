from logging import getLogger
lg = getLogger(__name__)

from datetime import timedelta

from numpy import squeeze, floor, ceil
from PySide.QtCore import QPointF, Qt
from PySide.QtGui import (QBrush,
                          QGraphicsItem,
                          QGraphicsScene,
                          QGraphicsSimpleTextItem,
                          QGraphicsView,
                          QPen,
                          )

from ..trans import Montage, Filter, Select
from .utils import Path


class Traces(QGraphicsView):
    """Main widget that contains the recordings to be plotted.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    y_scale: int or float
        multiply value by this scaling factor.
    y_distance : int or float
        distance between traces.
    y_scrollbar_value : int
        position of the vertical scrollbar
    data : dict
        where the data is stored as chan_name (group_name)
    time : numpy.ndarray
        vector containing the time points
    scene : instance of QGraphicsScene
        the main scene.
    idx_label : list of instance of QGraphicsSimpleTextItem

    idx_time : list of instance of QGraphicsSimpleTextItem

    time_pos : list of position of time
        we need to keep track of the position of y-label during creation

    Notes
    -----
    It doesn't handle NaN at the beginning, but actually well at the end.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        preferences = self.parent.preferences.values
        self.y_scale = preferences['traces/y_scale']
        self.y_distance = preferences['traces/y_distance']
        self.y_scrollbar_value = 0
        self.data = {}
        self.time = None

        self.scene = None
        self.idx_label = []
        self.idx_time = []
        self.time_pos = []

        self.create_traces()

    def create_traces(self):
        """Create empty scene."""
        lg.debug('Creating Traces widget')

    def update_traces(self):
        """Read and update the data to plot."""
        lg.debug('Updating Traces widget')

        window_start = self.parent.overview.window_start
        window_end = window_start + self.parent.overview.window_length
        dataset = self.parent.info.dataset

        chan_to_read = []
        for one_grp in self.parent.channels.groups:
            chan_to_read.extend(one_grp['chan_to_plot'] +
                                one_grp['ref_chan'])

        if not chan_to_read:
            return

        data = dataset.read_data(chan=chan_to_read,
                                 begtime=window_start,
                                 endtime=window_end)

        self.time = data.time
        self.data = {}
        for one_grp in self.parent.channels.groups:
            sel = Select(one_grp['chan_to_plot'] + one_grp['ref_chan'])
            mont = Montage(ref_chan=one_grp['ref_chan'])
            data1 = mont(sel(data))

            if one_grp['filter']['low_cut'] is not None:
                hpfilt = Filter(low_cut=one_grp['filter']['low_cut'],
                                s_freq=data.s_freq)
                data1 = hpfilt(data1)

            if one_grp['filter']['high_cut'] is not None:
                lpfilt = Filter(high_cut=one_grp['filter']['high_cut'],
                                s_freq=data.s_freq)
                data1 = lpfilt(data1)

            for chan in one_grp['chan_to_plot']:
                dat, _ = data1(chan=[chan])
                dat = squeeze(dat, axis=0) * one_grp['scale']
                chan_grp_name = chan + ' (' + one_grp['name'] + ')'
                self.data[chan_grp_name] = dat

        self.display_traces()
        self.parent.overview.mark_downloaded(window_start, window_end)

    def display_traces(self):
        """Display the recordings."""
        lg.debug('Displaying Traces widget')

        if self.scene is not None:
            self.y_scrollbar_value = self.verticalScrollBar().value()
            self.scene.clear()

        self.create_labels()
        self.create_time()

        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length

        time_height = max([x.boundingRect().height() for x in self.idx_time])
        preferences = self.parent.preferences.values
        label_width = window_length * float(preferences['traces/label_ratio'])

        self.scene = QGraphicsScene(window_start - label_width,
                                    0,
                                    window_length + label_width,
                                    len(self.idx_label) * self.y_distance +
                                    time_height)

        self.setScene(self.scene)
        self.add_labels()
        self.add_time()
        self.add_traces()

        if self.parent.bookmarks.bookmarks is not None:
            self.add_bookmarks()

        self.resizeEvent(None)
        self.verticalScrollBar().setValue(self.y_scrollbar_value)

    def create_labels(self):
        """Create the channel labels, but don't plot them yet."""

        self.idx_label = []
        for one_grp in self.parent.channels.groups:
            for one_label in one_grp['chan_to_plot']:
                item = QGraphicsSimpleTextItem(one_label)
                item.setBrush(QBrush(one_grp['color']))
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                self.idx_label.append(item)

    def create_time(self):
        """Create the time labels, but don't plot them yet.

        Notes
        -----
        Not very robust, because it uses seconds as integers.

        """
        start_time = self.parent.info.dataset.header['start_time']

        min_time = int(floor(min(self.time)))
        max_time = int(ceil(max(self.time)))

        preferences = self.parent.preferences.values
        n_time_labels = int(preferences['traces/n_time_labels'])
        step = int((max_time - min_time) / n_time_labels)

        self.idx_time = []
        self.time_pos = []
        for one_time in range(min_time, max_time, step):
            x_label = (start_time +
                       timedelta(seconds=one_time)).strftime('%H:%M:%S')
            item = QGraphicsSimpleTextItem(x_label)
            item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            self.idx_time.append(item)
            self.time_pos.append(QPointF(one_time,
                                         len(self.idx_label) *
                                         self.y_distance))

    def add_labels(self):
        """Add channel labels on the left."""
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length
        preferences = self.parent.preferences.values
        label_width = window_length * float(preferences['traces/label_ratio'])

        for row, one_label_item in enumerate(self.idx_label):
            self.scene.addItem(one_label_item)
            one_label_item.setPos(window_start - label_width,
                                  self.y_distance * row + self.y_distance / 2)

    def add_time(self):
        """Add time labels at the bottom."""
        for text, pos in zip(self.idx_time, self.time_pos):
            self.scene.addItem(text)
            text.setPos(pos)

    def add_traces(self):
        """Add traces based on self.data."""
        self.y_distance = self.y_distance

        row = 0
        for one_grp in self.parent.channels.groups:
            for one_chan in one_grp['chan_to_plot']:
                chan_name = one_chan + ' (' + one_grp['name'] + ')'
                dat = self.data[chan_name] * self.y_scale
                path = self.scene.addPath(Path(self.time, dat))
                path.setPen(QPen(one_grp['color']))
                path.setPos(0,
                            self.y_distance * row + self.y_distance / 2)
                row += 1

    def resizeEvent(self, event):
        """Resize scene so that it fits the whole widget.

        Parameters
        ----------
        event : instance of QtCore.QEvent
            not important

        Notes
        -----
        This function overwrites Qt function, therefore the non-standard
        name. Argument also depends on Qt.

        The function is used to change the scale of view, so that the scene
        fits the whole scene. There are two problems that I could not fix: 1)
        how to give the width of the label in absolute width, 2) how to strech
        scene just enough that it doesn't trigger a scrollbar. However, it's
        pretty good as it is now.

        """
        if self.scene is not None:
            ratio = self.width() / (self.scene.width() * 1.1)
            self.resetTransform()
            self.scale(ratio, 1)

    def add_bookmarks(self):
        """Add bookmarks on top of first plot."""
        lg.info('Adding bookmarks')
        bookmarks = self.parent.bookmarks.bookmarks
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length
        window_end = window_start + window_length
        time_height = max([x.boundingRect().height() for x in self.idx_time])

        for bm in bookmarks:
            if window_start <= bm['time'] <= window_end:
                lg.debug('Adding bookmark {} at {}'.format(bm['name'],
                                                           bm['time']))
                item = QGraphicsSimpleTextItem(bm['name'])
                item.setPos(bm['time'],
                            len(self.idx_label) * self.y_distance -
                            time_height)
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                item.setPen(QPen(Qt.red))
                self.scene.addItem(item)
