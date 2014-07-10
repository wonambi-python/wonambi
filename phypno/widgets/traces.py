"""Definition of the main widgets, with recordings.

"""
from logging import getLogger
lg = getLogger(__name__)

from copy import deepcopy
from datetime import timedelta

from numpy import floor, ceil, asarray, empty
from PyQt4.QtCore import QPointF, Qt
from PyQt4.QtGui import (QBrush,
                         QFormLayout,
                         QGraphicsItem,
                         QGraphicsScene,
                         QGraphicsSimpleTextItem,
                         QGraphicsView,
                         QGroupBox,
                         QPen,
                         QVBoxLayout,
                         )

from .. import ChanTime
from ..trans import Montage, Filter
from .utils import Path

from phypno.widgets.preferences import Config, FormFloat, FormInt


class ConfigTraces(Config):

    def __init__(self, update_widget):
        super().__init__('traces', update_widget)

    def create_config(self):

        box0 = QGroupBox('Signals')

        self.index['y_distance'] = FormFloat()
        self.index['y_scale'] = FormFloat()
        self.index['label_ratio'] = FormFloat()
        self.index['n_time_labels'] = FormInt()

        form_layout = QFormLayout()
        form_layout.addRow('Signal scaling',
                           self.index['y_scale'])
        form_layout.addRow('Distance between signals',
                           self.index['y_distance'])
        form_layout.addRow('Label width ratio',
                           self.index['label_ratio'])
        form_layout.addRow('Number of time labels',
                           self.index['n_time_labels'])

        box0.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


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
    data : instance of ChanTime
        filtered and reref'ed data
    scene : instance of QGraphicsScene
        the main scene.
    idx_label : list of instance of QGraphicsSimpleTextItem
        the channel labels on the y-axis
    idx_time : list of instance of QGraphicsSimpleTextItem
        the time labels on the x-axis
    time_pos : list of position of time
        we need to keep track of the position of y-label during creation

    Notes
    -----
    It doesn't handle NaN at the beginning, but actually well at the end.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigTraces(self.display_traces)

        self.y_scrollbar_value = 0
        self.data = None

        self.scene = None
        self.idx_label = []
        self.idx_time = []
        self.time_pos = []

        self.create_traces()

    def create_traces(self):
        """Create empty scene."""
        pass

    def update_traces(self):
        """Read and update the data to plot."""
        window_start = self.parent.overview.window_start
        window_end = window_start + self.parent.overview.window_length
        dataset = self.parent.info.dataset
        groups = self.parent.channels.groups

        chan_to_read = []
        for one_grp in groups:
            chan_to_read.extend(one_grp['chan_to_plot'] +
                                one_grp['ref_chan'])

        if not chan_to_read:
            return
        data = dataset.read_data(chan=chan_to_read,
                                 begtime=window_start,
                                 endtime=window_end)

        self.data = _create_data_to_plot(data,
                                         self.parent.channels.groups)
        self.display_traces()
        self.parent.overview.mark_downloaded(window_start, window_end)

    def display_traces(self):
        """Display the recordings."""
        if self.scene is not None:
            self.y_scrollbar_value = self.verticalScrollBar().value()
            self.scene.clear()

        self.create_labels()
        self.create_time()

        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length

        time_height = max([x.boundingRect().height() for x in self.idx_time])
        label_width = window_length * self.config.value['label_ratio']

        self.scene = QGraphicsScene(window_start - label_width,
                                    0,
                                    window_length + label_width,
                                    len(self.idx_label) *
                                    self.config.value['y_distance'] +
                                    time_height)

        self.setScene(self.scene)
        self.add_labels()
        self.add_time()
        self.add_traces()

        if self.parent.bookmarks.bookmarks is not None:
            self.add_bookmarks()

        self.resizeEvent(None)
        self.verticalScrollBar().setValue(self.y_scrollbar_value)
        self.parent.info.update_traces_info()

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
        min_time = int(floor(min(self.data.axis['time'][0])))
        max_time = int(ceil(max(self.data.axis['time'][0])))

        n_time_labels = self.config.value['n_time_labels']
        step = int((max_time - min_time) / n_time_labels)

        self.idx_time = []
        self.time_pos = []
        for one_time in range(min_time, max_time, step):
            x_label = (self.data.start_time +
                       timedelta(seconds=one_time)).strftime('%H:%M:%S')
            item = QGraphicsSimpleTextItem(x_label)
            item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            self.idx_time.append(item)
            self.time_pos.append(QPointF(one_time,
                                         len(self.idx_label) *
                                         self.config.value['y_distance']))

    def add_labels(self):
        """Add channel labels on the left."""
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length
        label_width = window_length * self.config.value['label_ratio']

        for row, one_label_item in enumerate(self.idx_label):
            self.scene.addItem(one_label_item)
            one_label_item.setPos(window_start - label_width,
                                  self.config.value['y_distance'] * row +
                                  self.config.value['y_distance'] / 2)

    def add_time(self):
        """Add time labels at the bottom."""
        for text, pos in zip(self.idx_time, self.time_pos):
            self.scene.addItem(text)
            text.setPos(pos)

    def add_traces(self):
        """Add traces based on self.data."""
        row = 0
        for one_grp in self.parent.channels.groups:
            for one_chan in one_grp['chan_to_plot']:
                chan_name = one_chan + ' (' + one_grp['name'] + ')'
                dat = self.data(trial=0, chan=chan_name) * self.config.value['y_scale']
                dat *= -1  # flip data, upside down
                path = self.scene.addPath(Path(self.data.axis['time'][0],
                                               dat))
                path.setPen(QPen(one_grp['color']))
                path.setPos(0, self.config.value['y_distance'] * row + self.config.value['y_distance'] / 2)
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
                            len(self.idx_label) * self.config.value['y_distance'] -
                            time_height)
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                item.setPen(QPen(Qt.red))
                self.scene.addItem(item)


def _create_data_to_plot(data, chan_groups):
    """Create data after montage and filtering.

    Parameters
    ----------
    data : instance of ChanTime
        the raw data
    chan_groups : list of dict
        information about channels to plot, to use as reference and about
        filtering etc.

    Returns
    -------
    instance of ChanTime
        data ready to be plotted.

    """
    # chan_to_plot only gives the number of channels to plot, for prealloc
    chan_to_plot = [one_chan for one_grp in chan_groups
                    for one_chan in one_grp['chan_to_plot']]

    output = ChanTime()
    output.s_freq = data.s_freq
    output.start_time = data.start_time
    output.axis['time'] = data.axis['time']
    output.axis['chan'] = empty(1, dtype='O')
    output.data = empty(1, dtype='O')
    output.data[0] = empty((len(chan_to_plot), data.number_of('time')[0]),
                           dtype='f')

    all_chan_grp_name = []
    i_ch = 0
    for one_grp in chan_groups:

        sel_data = _select_channels(data,
                                    one_grp['chan_to_plot'] +
                                    one_grp['ref_chan'])
        mont = Montage(ref_chan=one_grp['ref_chan'])
        data1 = mont(sel_data)

        if one_grp['filter']['low_cut'] is not None:
            hpfilt = Filter(low_cut=one_grp['filter']['low_cut'],
                            s_freq=data.s_freq)
            data1 = hpfilt(data1)

        if one_grp['filter']['high_cut'] is not None:
            lpfilt = Filter(high_cut=one_grp['filter']['high_cut'],
                            s_freq=data.s_freq)
            data1 = lpfilt(data1)

        for chan in one_grp['chan_to_plot']:
            chan_grp_name = chan + ' (' + one_grp['name'] + ')'
            all_chan_grp_name.append(chan_grp_name)

            dat = data1(chan=chan, trial=0)
            output.data[0][i_ch, :] = dat * one_grp['scale']
            i_ch += 1

    output.axis['chan'][0] = asarray(all_chan_grp_name, dtype='U')

    return output


def _select_channels(data, channels):
    """Select channels.

    Parameters
    ----------
    data : instance of ChanTime
        data with all the channels
    channels : list
        channels of interest

    Returns
    -------
    instance of ChanTime
        data with only channels of interest

    Notes
    -----
    This function does the same as phypno.trans.Select, but it's much faster.
    phypno.trans.Select needs to flexible for any data type, here we assume
    that we have one trial, and that channel is the first dimension.

    """
    data = deepcopy(data)
    chan_list = list(data.axis['chan'][0])
    idx_chan = [chan_list.index(i_chan) for i_chan in channels]
    data.data[0] = data.data[0][idx_chan, :]
    data.axis['chan'][0] = asarray(channels)

    return data
