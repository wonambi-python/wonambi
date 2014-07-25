"""Definition of the main widgets, with recordings.

"""
from logging import getLogger
lg = getLogger(__name__)

from copy import deepcopy
from datetime import timedelta

from numpy import abs, argmin, floor, ceil, asarray, empty, max, min, log2, power, pad
from PyQt4.QtCore import QPointF, Qt, QRectF
from PyQt4.QtGui import (QBrush,
                         QFormLayout,
                         QGraphicsItem,
                         QGraphicsRectItem,
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
from .settings import Config, FormFloat, FormInt


NoPen = QPen()
NoPen.setStyle(Qt.NoPen)

MINIMUM_N_SAMPLES = 32  # at least these samples to compute fft


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

        box1 = QGroupBox('Current Window')
        self.index['window_start'] = FormInt()
        self.index['window_length'] = FormInt()
        self.index['window_step'] = FormInt()

        form_layout = QFormLayout()
        form_layout.addRow('Window start time',
                           self.index['window_start'])
        form_layout.addRow('Window length',
                           self.index['window_length'])
        form_layout.addRow('Step size',
                           self.index['window_step'])
        box1.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addWidget(box1)
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
        self.chan = []
        self.chan_pos = []  # used later to find out which channel we're using
        self.chan_scale = []
        self.sel_chan = None
        self.sel_xy = (None, None)

        self.scene = None
        self.idx_label = []
        self.idx_time = []
        self.idx_sel = None  # selection
        self.idx_info = None
        self.time_pos = []
        self.idx_events = []  # events

        self.create_traces()

    def create_traces(self):
        """Create empty scene."""
        pass

    def update_traces(self):
        """Read and update the data to plot."""
        window_start = self.parent.value('window_start')
        window_end = window_start + self.parent.value('window_length')
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

        self.data = _create_data_to_plot(data, self.parent.channels.groups)
        self.display_traces()
        self.parent.overview.mark_downloaded(window_start, window_end)

    def display_traces(self):
        """Display the recordings."""
        if self.scene is not None:
            self.y_scrollbar_value = self.verticalScrollBar().value()
            self.scene.clear()

        self.create_labels()
        self.create_time()

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')

        time_height = max([x.boundingRect().height() for x in self.idx_time])
        label_width = window_length * self.parent.value('label_ratio')

        self.scene = QGraphicsScene(window_start - label_width,
                                    0,
                                    window_length + label_width,
                                    len(self.idx_label) *
                                    self.parent.value('y_distance') +
                                    time_height)

        self.setScene(self.scene)
        self.add_labels()
        self.add_time()
        self.add_traces()
        self.display_markers()
        self.display_events()

        self.resizeEvent(None)
        self.verticalScrollBar().setValue(self.y_scrollbar_value)
        self.parent.info.display_view()

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

        n_time_labels = self.parent.value('n_time_labels')
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
                                         self.parent.value('y_distance')))

    def add_labels(self):
        """Add channel labels on the left."""
        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        label_width = window_length * self.parent.value('label_ratio')

        for row, one_label_item in enumerate(self.idx_label):
            self.scene.addItem(one_label_item)
            one_label_item.setPos(window_start - label_width,
                                  self.parent.value('y_distance') * row +
                                  self.parent.value('y_distance') / 2)

    def add_time(self):
        """Add time labels at the bottom."""
        for text, pos in zip(self.idx_time, self.time_pos):
            self.scene.addItem(text)
            text.setPos(pos)

    def add_traces(self):
        """Add traces based on self.data."""
        self.chan = []
        self.chan_pos = []
        self.chan_scale = []

        row = 0
        for one_grp in self.parent.channels.groups:
            for one_chan in one_grp['chan_to_plot']:
                chan_name = one_chan + ' (' + one_grp['name'] + ')'
                self.chan.append(chan_name)
                self.chan_scale.append(one_grp['scale'])
                dat = (self.data(trial=0, chan=chan_name) *
                       self.parent.value('y_scale'))
                dat *= -1  # flip data, upside down
                path = self.scene.addPath(Path(self.data.axis['time'][0],
                                               dat))
                path.setPen(QPen(one_grp['color']))

                chan_pos = (self.parent.value('y_distance') * row +
                            self.parent.value('y_distance') / 2)
                self.chan_pos.append(chan_pos)
                path.setPos(0, chan_pos)
                row += 1

    def display_markers(self):
        """Add bookmarks on top of first plot."""
        if self.scene is None:
            return

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        window_end = window_start + window_length
        time_height = max([x.boundingRect().height() for x in self.idx_time])

        # TODO: don't repeat code twice
        if self.parent.notes.annot is not None:
            for mrk in self.parent.notes.annot.get_markers():
                if window_start <= mrk['time'] <= window_end:
                    item = QGraphicsSimpleTextItem(mrk['name'])
                    item.setPos(mrk['time'],
                                len(self.idx_label) *
                                self.parent.value('y_distance') -
                                time_height)
                    item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                    item.setPen(QPen(Qt.red))
                    self.scene.addItem(item)

        if self.parent.notes.dataset_markers is not None:
            for mrk in self.parent.notes.dataset_markers:
                if window_start <= mrk['time'] <= window_end:
                    item = QGraphicsSimpleTextItem(mrk['name'])
                    item.setPos(mrk['time'],
                                len(self.idx_label) *
                                self.parent.value('y_distance') -
                                time_height)
                    item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                    self.scene.addItem(item)

    def display_events(self):
        """Add events on top of first plot."""
        if self.scene is None:
            return

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        window_end = window_start + window_length
        time_height = max([x.boundingRect().height() for x in self.idx_time])

        # TODO: don't repeat code twice
        if self.parent.notes.annot is not None:

            events = self.parent.notes.annot.get_events(time=(window_start,
                                                              window_end))
            for evt in events:
                rect = QGraphicsRectItem(evt['start'],
                                         0,
                                         evt['end'] - evt['start'],
                                         time_height)
                rect.setPen(NoPen)
                rect.setBrush(QBrush(Qt.cyan))  # TODO: depend on events
                self.scene.addItem(rect)

    def mousePressEvent(self, event):
        """Jump to window when user clicks on overview.

        Parameters
        ----------
        event : instance of QtCore.QEvent
            it contains the position that was clicked.

        """
        if self.parent.notes.action['new_marker'].isChecked():
            x_in_scene = self.mapToScene(event.pos()).x()

            # max resolution = sampling frequency
            # in case there is no data
            s_freq = self.parent.info.dataset.header['s_freq']
            time = int(x_in_scene * s_freq) / s_freq
            self.parent.notes.add_marker(time)

        else:
            """the same info is used by action['new_event'].isChecked():"""
            xy_scene = self.mapToScene(event.pos())
            chan_idx = argmin(abs(asarray(self.chan_pos) - xy_scene.y()))
            self.sel_chan = chan_idx
            self.sel_xy = (xy_scene.x(), xy_scene.y())

    def mouseMoveEvent(self, event):
        """
        """
        if self.idx_sel is not None:
            self.scene.removeItem(self.idx_sel)

        if self.parent.notes.action['new_event'].isChecked():
            xy_scene = self.mapToScene(event.pos())
            time_height = max([x.boundingRect().height() for x in self.idx_time])
            pos = QRectF(self.sel_xy[0],
                         0,
                         xy_scene.x() - self.sel_xy[0],
                         time_height)
            self.idx_sel = QGraphicsRectItem(pos.normalized())
            self.idx_sel.setPen(NoPen)
            self.idx_sel.setBrush(QBrush(Qt.cyan))

            self.scene.addItem(self.idx_sel)
            return

        xy_scene = self.mapToScene(event.pos())
        pos = QRectF(self.sel_xy[0], self.sel_xy[1],
                     xy_scene.x() - self.sel_xy[0],
                     xy_scene.y() - self.sel_xy[1])
        self.idx_sel = QGraphicsRectItem(pos.normalized())
        self.scene.addItem(self.idx_sel)

        if self.idx_info is not None:
            self.scene.removeItem(self.idx_info)

        duration = '{0:0.2f}s'.format(abs(xy_scene.x() - self.sel_xy[0]))

        # get y-size, based on scaling too
        y = abs(xy_scene.y() - self.sel_xy[1])
        scale = self.parent.value('y_scale') * self.chan_scale[self.sel_chan]
        height = '{0:0.3f}uV'.format(y / scale)

        self.idx_info = TextItem_with_BG()
        self.idx_info.setText(duration + ' ' + height)
        self.idx_info.setPos(self.sel_xy[0], self.sel_xy[1])

        self.scene.addItem(self.idx_info)

        trial = 0
        time = self.parent.traces.data.axis['time'][trial]
        beg_win = min((self.sel_xy[0], xy_scene.x()))
        end_win = max((self.sel_xy[0], xy_scene.x()))
        time_of_interest = time[(time >= beg_win) & (time < end_win)]
        if len(time_of_interest) > MINIMUM_N_SAMPLES:
            data = self.parent.traces.data(trial=trial,
                                           chan=self.chan[self.sel_chan],
                                           time=time_of_interest)
            n_data = len(data)
            n_pad = (power(2, ceil(log2(n_data))) - n_data) / 2
            data = pad(data, (ceil(n_pad), floor(n_pad)), 'constant')

            self.parent.spectrum.display_spectrum(data)

    def mouseReleaseEvent(self, event):

        if self.parent.notes.action['new_event'].isChecked():
            x_in_scene = self.mapToScene(event.pos()).x()

            eventtype = self.parent.notes.idx_eventtype.currentText()
            # max resolution = sampling frequency
            # in case there is no data
            s_freq = self.parent.info.dataset.header['s_freq']
            at_s_freq = lambda x: int(x * s_freq) / s_freq
            start = at_s_freq(self.sel_xy[0])
            end = at_s_freq(x_in_scene)
            time = (start, end)
            self.parent.notes.add_event(eventtype, time)

        else:

            self.sel_chan = None
            self.sel_xy = (None, None)

            if self.idx_sel is not None:
                self.scene.removeItem(self.idx_sel)
            self.idx_sel = None

            if self.idx_info is not None:
                self.scene.removeItem(self.idx_info)
            self.idx_info = None

            # restore spectrum
            self.parent.spectrum.display_spectrum()

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

    def reset(self):
        self.y_scrollbar_value = 0
        self.data = None
        self.chan = []
        self.chan_pos = []
        self.chan_scale = []
        self.sel_chan = None
        self.sel_xy = (None, None)

        if self.scene is not None:
            self.scene.clear()
        self.scene = None
        self.idx_sel = None
        self.idx_info = None
        self.idx_label = []
        self.idx_time = []
        self.time_pos = []


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


class TextItem_with_BG(QGraphicsSimpleTextItem):
    """Class to draw text with black background (easier to read).

    """
    def __init__(self):
        super().__init__()

        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setBrush(QBrush(Qt.white))

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(Qt.black))
        painter.drawRect(self.boundingRect())
        super().paint(painter, option, widget)
