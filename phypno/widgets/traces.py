"""Definition of the main widgets, with recordings.

"""
from logging import getLogger
lg = getLogger(__name__)

from copy import deepcopy
from datetime import timedelta
from functools import partial

from numpy import (abs, arange, argmin, asarray, ceil, empty, floor, max, min,
                   log2, pad, power)
from PyQt4.QtCore import QPointF, Qt, QRectF
from PyQt4.QtGui import (QAction,
                         QBrush,
                         QColor,
                         QFormLayout,
                         QGraphicsItem,
                         QGraphicsRectItem,
                         QGraphicsScene,
                         QGraphicsSimpleTextItem,
                         QGraphicsView,
                         QGroupBox,
                         QIcon,
                         QKeySequence,
                         QPen,
                         QVBoxLayout,
                         )

from .. import ChanTime
from ..trans import Montage, Filter
from .settings import Config, FormFloat, FormInt, FormBool
from .utils import convert_name_to_color, ICON, Path, TextItem_with_BG

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

        self.index['grid_x'] = FormBool('Grid on time axis')
        self.index['grid_xtick'] = FormFloat()
        self.index['grid_y'] = FormBool('Grid on voltage axis')

        form_layout = QFormLayout()
        box1.setLayout(form_layout)
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

        self.create_action()

    def create_action(self):
        actions = {}

        act = QAction(QIcon(ICON['step_prev']), 'Previous Step', self)
        act.setShortcut(QKeySequence.MoveToPreviousChar)
        act.triggered.connect(self.step_prev)
        actions['step_prev'] = act

        act = QAction(QIcon(ICON['step_next']), 'Next Step', self)
        act.setShortcut(QKeySequence.MoveToNextChar)
        act.triggered.connect(self.step_next)
        actions['step_next'] = act

        act = QAction(QIcon(ICON['page_prev']), 'Previous Page', self)
        act.setShortcut(QKeySequence.MoveToPreviousPage)
        act.triggered.connect(self.page_prev)
        actions['page_prev'] = act

        act = QAction(QIcon(ICON['page_next']), 'Next Page', self)
        act.setShortcut(QKeySequence.MoveToNextPage)
        act.triggered.connect(self.page_next)
        actions['page_next'] = act

        act = QAction(QIcon(ICON['zoomprev']), 'Wider Time Window', self)
        act.setShortcut(QKeySequence.ZoomIn)
        act.triggered.connect(self.X_more)
        actions['X_more'] = act

        act = QAction(QIcon(ICON['zoomnext']), 'Narrower Time Window', self)
        act.setShortcut(QKeySequence.ZoomOut)
        act.triggered.connect(self.X_less)
        actions['X_less'] = act

        act = QAction(QIcon(ICON['zoomin']), 'Larger Amplitude', self)
        act.setShortcut(QKeySequence.MoveToPreviousLine)
        act.triggered.connect(self.Y_more)
        actions['Y_less'] = act

        act = QAction(QIcon(ICON['zoomout']), 'Smaller Amplitude', self)
        act.setShortcut(QKeySequence.MoveToNextLine)
        act.triggered.connect(self.Y_less)
        actions['Y_more'] = act

        act = QAction(QIcon(ICON['ydist_more']), 'Larger Y Distance', self)
        act.triggered.connect(self.Y_wider)
        actions['Y_wider'] = act

        act = QAction(QIcon(ICON['ydist_less']), 'Smaller Y Distance', self)
        act.triggered.connect(self.Y_tighter)
        actions['Y_tighter'] = act

        act = QAction(QIcon(ICON['chronometer']), '6 Hours Earlier', self)
        act.triggered.connect(partial(self.add_time, -6 * 60 * 60))
        actions['addtime_-6h'] = act

        act = QAction(QIcon(ICON['chronometer']), '1 Hour Earlier', self)
        act.triggered.connect(partial(self.add_time, -60 * 60))
        actions['addtime_-1h'] = act

        act = QAction(QIcon(ICON['chronometer']), '10 Minutes Earlier', self)
        act.triggered.connect(partial(self.add_time, -10 * 60))
        actions['addtime_-10min'] = act

        act = QAction(QIcon(ICON['chronometer']), '10 Minutes Later', self)
        act.triggered.connect(partial(self.add_time, 10 * 60))
        actions['addtime_10min'] = act

        act = QAction(QIcon(ICON['chronometer']), '1 Hour Later', self)
        act.triggered.connect(partial(self.add_time, 60 * 60))
        actions['addtime_1h'] = act

        act = QAction(QIcon(ICON['chronometer']), '6 Hours Later', self)
        act.triggered.connect(partial(self.add_time, 6 * 60 * 60))
        actions['addtime_6h'] = act

        self.action = actions

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
        self.add_time_labels()
        self.add_traces()
        self.display_grid()
        self.display_notes()

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

    def add_time_labels(self):
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

    def display_grid(self):
        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        window_end = window_start + window_length

        if self.parent.value('grid_x'):
            x_tick = self.parent.value('grid_xtick')
            x_ticks = arange(window_start, window_end + x_tick, x_tick)
            for x in x_ticks:
                x_pos = [x, x]
                y_pos = [0,
                         self.parent.value('y_distance') * len(self.idx_label)]
                path = self.scene.addPath(Path(x_pos, y_pos))
                path.setPen(QPen(Qt.DotLine))

        if self.parent.value('grid_y'):
            for one_label_item in self.idx_label:
                x_pos = [window_start, window_end]
                y_pos = [one_label_item.y(), one_label_item.y()]
                path = self.scene.addPath(Path(x_pos, y_pos))
                path.setPen(QPen(Qt.DotLine))

    def display_notes(self):
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
        y_distance = self.parent.value('y_distance')

        annot_markers = []
        events = []
        dataset_markers = []
        if self.parent.notes.dataset_markers is not None:
            if self.parent.value('dataset_marker_show'):
                dataset_markers = self.parent.notes.dataset_markers

        if self.parent.notes.annot is not None:
            if self.parent.value('annot_marker_show'):
                annot_markers = self.parent.notes.annot.get_markers()

            if self.parent.value('annot_marker_show'):
                events = self.parent.notes.annot.get_events(time=(window_start,
                                                                  window_end))
        markers = dataset_markers + annot_markers + events

        for mrk in markers:
            if window_start <= mrk['end'] and window_end >= mrk['start']:

                mrk_start = max((mrk['start'], window_start))
                mrk_end = min((mrk['end'], window_end))

                if mrk in dataset_markers:
                    color = QColor(self.parent.value('dataset_marker_color'))
                if mrk in annot_markers:
                    color = QColor(self.parent.value('annot_marker_color'))
                if mrk in events:
                    color = convert_name_to_color(mrk['name'])

                item = QGraphicsRectItem(mrk_start, 0,
                                         mrk_end - mrk_start,
                                         len(self.idx_label) * y_distance)
                item.setPen(color)
                item.setBrush(color)
                item.setZValue(-8)
                self.scene.addItem(item)

                item = TextItem_with_BG(color.darker(200))
                item.setText(mrk['name'])
                item.setPos(mrk['start'],
                            len(self.idx_label) *
                            self.parent.value('y_distance'))
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                item.setRotation(-90)
                self.scene.addItem(item)

    def step_prev(self):
        """Go to the previous step."""
        window_start = (self.parent.value('window_start') -
                        self.parent.value('window_length') /
                        self.parent.value('window_step'))
        self.parent.overview.update_position(window_start)

    def step_next(self):
        """Go to the next step."""
        window_start = (self.parent.value('window_start') +
                        self.parent.value('window_length') /
                        self.parent.value('window_step'))
        self.parent.overview.update_position(window_start)

    def page_prev(self):
        """Go to the previous page."""
        window_start = (self.parent.value('window_start') -
                        self.parent.value('window_length'))
        self.parent.overview.update_position(window_start)

    def page_next(self):
        """Go to the next page."""
        window_start = (self.parent.value('window_start')
                        + self.parent.value('window_length'))
        self.parent.overview.update_position(window_start)

    def add_time(self, extra_time):
        """Go to the predefined time forward."""
        window_start = self.parent.value('window_start') + extra_time
        self.parent.overview.update_position(window_start)

    def X_more(self):
        """Zoom in on the x-axis."""
        self.parent.value('window_length',
                          self.parent.value('window_length') * 2)
        self.parent.overview.display_current()
        self.parent.overview.update_position()

    def X_less(self):
        """Zoom out on the x-axis."""
        self.parent.value('window_length',
                          self.parent.value('window_length') / 2)
        self.parent.overview.display_current()
        self.parent.overview.update_position()

    def X_length(self, new_window_length):
        """Use presets for length of the window."""
        self.parent.value('window_length', new_window_length)
        self.parent.overview.display_current()
        self.parent.overview.update_position()

    def Y_more(self):
        """Increase the amplitude."""
        self.parent.value('y_scale', self.parent.value('y_scale') * 2)
        self.parent.traces.display()

    def Y_less(self):
        """Decrease the amplitude."""
        self.parent.value('y_scale', self.parent.value('y_scale') / 2)
        self.parent.traces.display()

    def Y_ampl(self, new_y_scale):
        """Make amplitude on Y axis using predefined values"""
        self.parent.value('y_scale', new_y_scale)
        self.parent.traces.display()

    def Y_wider(self):
        """Increase the distance of the lines."""
        self.parent.value('y_distance', self.parent.value('y_distance') * 1.4)
        self.parent.traces.display()

    def Y_tighter(self):
        """Decrease the distance of the lines."""
        self.parent.value('y_distance', self.parent.value('y_distance') / 1.4)
        self.parent.traces.display()

    def Y_dist(self, new_y_distance):
        """Use preset values for the distance between lines."""
        self.parent.value('y_distance', new_y_distance)
        self.parent.traces.display()

    def mousePressEvent(self, event):
        """Create a marker or start selection

        Parameters
        ----------
        event : instance of QtCore.QEvent
            it contains the position that was clicked.

        """
        xy_scene = self.mapToScene(event.pos())
        chan_idx = argmin(abs(asarray(self.chan_pos) - xy_scene.y()))
        self.sel_chan = chan_idx
        self.sel_xy = (xy_scene.x(), xy_scene.y())

        chk_marker = self.parent.notes.action['new_marker'].isChecked()
        chk_event = self.parent.notes.action['new_event'].isChecked()

        if not (chk_marker or chk_event):
            channame = self.chan[self.sel_chan] + ' in selected window'
            self.parent.spectrum.show_channame(channame)

    def mouseMoveEvent(self, event):
        """
        """
        # lg.debug('IDX_SEL: ' + str(self.idx_sel))
        if self.idx_sel in self.scene.items():
            self.scene.removeItem(self.idx_sel)
            self.idx_sel = None

        chk_marker = self.parent.notes.action['new_marker'].isChecked()
        chk_event = self.parent.notes.action['new_event'].isChecked()

        if chk_marker or chk_event:
            xy_scene = self.mapToScene(event.pos())
            y_distance = self.parent.value('y_distance')
            pos = QRectF(self.sel_xy[0],
                         0,
                         xy_scene.x() - self.sel_xy[0],
                         len(self.idx_label) * y_distance)
            item = QGraphicsRectItem(pos.normalized())
            item.setPen(NoPen)

            if chk_marker:
                color = QColor(self.parent.value('annot_marker_color'))

            elif chk_event:
                eventtype = self.parent.notes.idx_eventtype.currentText()
                color = convert_name_to_color(eventtype)

            item.setBrush(QBrush(color.lighter(150)))
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

        chk_marker = self.parent.notes.action['new_marker'].isChecked()
        chk_event = self.parent.notes.action['new_event'].isChecked()

        if chk_marker or chk_event:

            x_in_scene = self.mapToScene(event.pos()).x()

            # it can happen that selection is empty (f.e. double-click)
            if self.sel_xy[0] is not None:
                # max resolution = sampling frequency
                # in case there is no data
                s_freq = self.parent.info.dataset.header['s_freq']
                at_s_freq = lambda x: round(x * s_freq) / s_freq
                start = at_s_freq(self.sel_xy[0])
                end = at_s_freq(x_in_scene)

                if abs(end - start) < self.parent.value('min_marker_dur'):
                    end = start

                if start <= end:
                    time = (start, end)
                else:
                    time = (end, start)

                if chk_marker:
                    self.parent.notes.add_marker(time)

                elif chk_event:
                    eventtype = self.parent.notes.idx_eventtype.currentText()
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

        if one_grp['hp'] is not None:
            hpfilt = Filter(low_cut=one_grp['hp'],
                            s_freq=data.s_freq)
            data1 = hpfilt(data1)

        if one_grp['lp'] is not None:
            lpfilt = Filter(high_cut=one_grp['lp'],
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
