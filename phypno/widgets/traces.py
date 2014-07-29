"""Definition of the main widgets, with recordings.

"""
from logging import getLogger
lg = getLogger(__name__)

from copy import deepcopy
from datetime import timedelta

from numpy import (abs, argmin, asarray, ceil, empty, floor, max, min, log2,
                   pad, power)
from PyQt4.QtCore import QPointF, Qt, QRectF
from PyQt4.QtGui import (QBrush,
                         QColor,
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
from .settings import Config, FormFloat, FormInt, FormBool


NoPen = QPen()
NoPen.setStyle(Qt.NoPen)

MINIMUM_N_SAMPLES = 32  # at least this number of samples to compute fft


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
        box0.setLayout(form_layout)
        form_layout.addRow('Signal scaling',
                           self.index['y_scale'])
        form_layout.addRow('Distance between signals',
                           self.index['y_distance'])
        form_layout.addRow('Label width ratio',
                           self.index['label_ratio'])
        form_layout.addRow('Number of time labels',
                           self.index['n_time_labels'])

        box1 = QGroupBox('Grid')

        self.index['grid_border'] = FormBool('Border')
        self.index['grid_x'] = FormBool('Grid on time axis')
        self.index['grid_xtick'] = FormFloat()
        self.index['grid_y'] = FormBool('Grid on voltage axis')

        form_layout = QFormLayout()
        box1.setLayout(form_layout)
        form_layout.addRow(self.index['grid_border'])
        form_layout.addRow(self.index['grid_x'])
        form_layout.addRow('Tick every (s)', self.index['grid_xtick'])
        form_layout.addRow(self.index['grid_y'])

        box2 = QGroupBox('Current Window')
        self.index['window_start'] = FormInt()
        self.index['window_length'] = FormInt()
        self.index['window_step'] = FormInt()

        form_layout = QFormLayout()
        box2.setLayout(form_layout)
        form_layout.addRow('Window start time',
                           self.index['window_start'])
        form_layout.addRow('Window length',
                           self.index['window_length'])
        form_layout.addRow('Step size',
                           self.index['window_step'])

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addWidget(box1)
        main_layout.addWidget(box2)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


class Traces(QGraphicsView):
    """Main widget that contains the recordings to be plotted.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    config : instance of ConfigTraces
        settings for this widget

    y_scrollbar_value : int
        position of the vertical scrollbar
    data : instance of ChanTime
        filtered and reref'ed data

    chan : list of str
        list of channels (labels and channel group)
    chan_pos : list of int
        y-position of each channel (based on value at 0)
    chan_scale : list of float
        scaling factor for each channel
    time_pos : list of QPointF
        we need to keep track of the position of time label during creation
    sel_chan : int
        index of self.chan of the first selected channel
    sel_xy : tuple of 2 floats
        x and y position of the first selected point

    scene : instance of QGraphicsScene
        the main scene.
    idx_label : list of instance of QGraphicsSimpleTextItem
        the channel labels on the y-axis
    idx_time : list of instance of QGraphicsSimpleTextItem
        the time labels on the x-axis
    idx_sel : instance of QGraphicsRectItem
        the rectangle showing the selection (both for selection and event)
    idx_info : instance of QGraphicsSimpleTextItem
        the rectangle showing the selection

    Notes
    -----
    TODO: maybe create an empty scene to add markers

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigTraces(self.display)

        self.y_scrollbar_value = 0
        self.data = None
        self.chan = []
        self.chan_pos = []  # used later to find out which channel we're using
        self.chan_scale = []
        self.time_pos = []
        self.sel_chan = None
        self.sel_xy = (None, None)

        self.scene = None
        self.idx_label = []
        self.idx_time = []
        self.idx_sel = None
        self.idx_info = None

    def read_data(self):
        """Read the data to plot."""
        window_start = self.parent.value('window_start')
        window_end = window_start + self.parent.value('window_length')
        dataset = self.parent.info.dataset
        groups = self.parent.channels.groups

        chan_to_read = []
        for one_grp in groups:
            chan_to_read.extend(one_grp['chan_to_plot'] + one_grp['ref_chan'])

        if not chan_to_read:
            return
        data = dataset.read_data(chan=chan_to_read,
                                 begtime=window_start,
                                 endtime=window_end)

        self.data = _create_data_to_plot(data, self.parent.channels.groups)
        self.parent.overview.mark_downloaded(window_start, window_end)

    def display(self):
        """Display the recordings."""
        if self.data is None:
            return

        if self.scene is not None:
            self.y_scrollbar_value = self.verticalScrollBar().value()
            self.scene.clear()

        self.create_labels()
        self.create_time()

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')

        time_height = max([x.boundingRect().height() for x in self.idx_time])
        label_width = window_length * self.parent.value('label_ratio')
        scene_height = (len(self.idx_label) * self.parent.value('y_distance') +
                        time_height)

        self.scene = QGraphicsScene(window_start - label_width,
                                    0,
                                    window_length + label_width,
                                    scene_height)

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
        """Create the channel labels, but don't plot them yet.

        Notes
        -----
        It's necessary to have the width of the labels, so that we can adjust
        the main scene.
        """
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
        It's necessary to have the height of the time labels, so that we can
        adjust the main scene.

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

                # channel name
                chan_name = one_chan + ' (' + one_grp['name'] + ')'

                # trace
                dat = (self.data(trial=0, chan=chan_name) *
                       self.parent.value('y_scale'))
                dat *= -1  # flip data, upside down
                path = self.scene.addPath(Path(self.data.axis['time'][0],
                                               dat))
                path.setPen(QPen(one_grp['color']))

                # adjust position
                chan_pos = (self.parent.value('y_distance') * row +
                            self.parent.value('y_distance') / 2)
                path.setPos(0, chan_pos)
                row += 1

                self.chan.append(chan_name)
                self.chan_scale.append(one_grp['scale'])
                self.chan_pos.append(chan_pos)

    def display_markers(self):
        """Add markers on top of first plot.

        Notes
        -----
        This function should be called by traces.display only, even when we
        only add markers. It's because sometimes we delete markers.

        There are two approaches: either we redo the whole figure or we
        keep track of the markers and we delete only those. Here we go for the
        first approach.
        """
        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        window_end = window_start + window_length
        time_height = max([x.boundingRect().height() for x in self.idx_time])

        annot_markers = []
        if self.parent.notes.annot is not None:
            annot_markers = self.parent.notes.annot.get_markers()

        dataset_markers = []
        if self.parent.notes.dataset_markers is not None:
            dataset_markers = self.parent.notes.dataset_markers

        markers = annot_markers + dataset_markers

        for mrk in markers:
            if window_start <= mrk['time'] <= window_end:

                item = QGraphicsSimpleTextItem(mrk['name'])
                item.setPos(mrk['time'],
                            len(self.idx_label) *
                            self.parent.value('y_distance') -
                            time_height)
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                self.scene.addItem(item)

                if mrk in annot_markers:
                    color = self.parent.value('annot_marker_color')
                if mrk in dataset_markers:
                    color = self.parent.value('dataset_marker_color')
                item.setBrush(QBrush(QColor(color)))

    def display_events(self):
        """Add events on top of first plot.

        Notes
        -----
        This function should be called by traces.display only, even when we
        only add events. It's because sometimes we delete events.

        """
        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        window_end = window_start + window_length
        y_distance = self.parent.value('y_distance')

        if self.parent.notes.annot is not None:

            events = self.parent.notes.annot.get_events(time=(window_start,
                                                              window_end))
            for evt in events:
                evt_start = max((evt['start'], window_start))
                evt_end = min((evt['end'], window_end))

                rect = QGraphicsRectItem(evt_start,
                                         0,
                                         evt_end - evt_start,
                                         len(self.idx_label) * y_distance)
                rect.setPen(NoPen)
                rect.setBrush(QBrush(Qt.cyan))  # TODO: depend on events
                rect.setZValue(-10)
                self.scene.addItem(rect)

    def mousePressEvent(self, event):
        """Create a marker or start selection

        Parameters
        ----------
        event : instance of QtCore.QEvent
            it contains the position that was clicked.

        """
        if self.parent.notes.action['new_marker'].isChecked():
            x_in_scene = self.mapToScene(event.pos()).x()

            if self.parent.info.dataset is not None:
                # max resolution = sampling frequency
                s_freq = self.parent.info.dataset.header['s_freq']
                time = round(x_in_scene * s_freq) / s_freq

            else:
                # create marker at the beginning of the window
                time = self.parent.value('window_start')

            self.parent.notes.add_marker(time)

        else:
            """the same info is used by action['new_event'].isChecked():"""
            xy_scene = self.mapToScene(event.pos())
            chan_idx = argmin(abs(asarray(self.chan_pos) - xy_scene.y()))
            self.sel_chan = chan_idx
            self.sel_xy = (xy_scene.x(), xy_scene.y())

            if not self.parent.notes.action['new_event'].isChecked():
                channame = self.chan[self.sel_chan] + ' in selected window'
                self.parent.spectrum.show_channame(channame)

    def mouseMoveEvent(self, event):
        """
        """
        # lg.debug('IDX_SEL: ' + str(self.idx_sel))
        if self.idx_sel in self.scene.items():
            self.scene.removeItem(self.idx_sel)
            self.idx_sel = None

        if self.parent.notes.action['new_event'].isChecked():
            xy_scene = self.mapToScene(event.pos())
            y_distance = self.parent.value('y_distance')
            pos = QRectF(self.sel_xy[0],
                         0,
                         xy_scene.x() - self.sel_xy[0],
                         len(self.idx_label) * y_distance)
            item = QGraphicsRectItem(pos.normalized())
            item.setPen(NoPen)
            item.setBrush(QBrush(Qt.cyan))
            item.setZValue(-10)
            self.scene.addItem(item)
            self.idx_sel = item
            return

        xy_scene = self.mapToScene(event.pos())
        pos = QRectF(self.sel_xy[0], self.sel_xy[1],
                     xy_scene.x() - self.sel_xy[0],
                     xy_scene.y() - self.sel_xy[1])
        self.idx_sel = QGraphicsRectItem(pos.normalized())
        self.scene.addItem(self.idx_sel)

        if self.idx_info in self.scene.items():
            self.scene.removeItem(self.idx_info)

        duration = '{0:0.2f}s'.format(abs(xy_scene.x() - self.sel_xy[0]))

        # get y-size, based on scaling too
        y = abs(xy_scene.y() - self.sel_xy[1])
        scale = self.parent.value('y_scale') * self.chan_scale[self.sel_chan]
        height = '{0:0.3f}uV'.format(y / scale)

        item = TextItem_with_BG()
        item.setText(duration + ' ' + height)
        item.setPos(self.sel_xy[0], self.sel_xy[1])
        self.scene.addItem(item)
        self.idx_info = item

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

            self.parent.spectrum.display(data)

    def mouseReleaseEvent(self, event):

        if self.parent.notes.action['new_event'].isChecked():
            x_in_scene = self.mapToScene(event.pos()).x()

            eventtype = self.parent.notes.idx_eventtype.currentText()
            # max resolution = sampling frequency
            # in case there is no data
            s_freq = self.parent.info.dataset.header['s_freq']
            at_s_freq = lambda x: round(x * s_freq) / s_freq
            start = at_s_freq(self.sel_xy[0])
            end = at_s_freq(x_in_scene)
            time = (start, end)
            self.parent.notes.add_event(eventtype, time)

        else:  # normal selection

            if self.idx_info in self.scene.items():
                self.scene.removeItem(self.idx_info)
            self.idx_info = None

            # restore spectrum
            self.parent.spectrum.update()

        # general garbage collection
        self.sel_chan = None
        self.sel_xy = (None, None)

        if self.idx_sel in self.scene.items():
            self.scene.removeItem(self.idx_sel)
            self.idx_sel = None

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
