"""Definition of the main widgets, with recordings.
"""
from datetime import time, datetime, timedelta
from functools import partial
from logging import getLogger
from re import compile

from numpy import (abs, amax, arange, argmin, around, asarray, ceil, empty, floor,
                   in1d, max, min, linspace, log2, logical_or, nan_to_num,
                   nanmean, pad, power)

from PyQt5.QtCore import QPointF, Qt, QRectF
from PyQt5.QtGui import (QBrush,
                         QColor,
                         QIcon,
                         QKeyEvent,
                         QKeySequence,
                         QPen,
                         )
from PyQt5.QtWidgets import (QAction,
                             QErrorMessage,
                             QFormLayout,
                             QGraphicsItem,
                             QGraphicsRectItem,
                             QGraphicsScene,
                             QGraphicsSimpleTextItem,
                             QGraphicsView,
                             QGroupBox,
                             QInputDialog,
                             QMessageBox,
                             QVBoxLayout,
                             )

from .. import ChanTime
from ..trans import montage, filter_, _select_channels
from .settings import Config
from .utils import (convert_name_to_color,
                    ICON,
                    LINE_COLOR,
                    LINE_WIDTH,
                    Path,
                    RectMarker,
                    TextItem_with_BG,
                    FormFloat,
                    FormInt,
                    FormBool,
                    export_graphics,
                    )


lg = getLogger(__name__)

# undo the chan + (group) naming
take_raw_name = lambda x: ' ('.join(x.split(' (')[:-1])

NoPen = QPen()
NoPen.setStyle(Qt.NoPen)

MINIMUM_N_SAMPLES = 32  # at least this number of samples to compute fft

CHECK_TIME_STR = compile('[0-9:-]+$')


class ConfigTraces(Config):
    """Widget with preferences in Settings window for Overview."""
    def __init__(self, update_widget):
        super().__init__('traces', update_widget)

    def create_config(self):

        box0 = QGroupBox('Signals')

        self.index['y_distance'] = FormFloat()
        self.index['y_scale'] = FormFloat()
        self.index['label_ratio'] = FormFloat()
        self.index['n_time_labels'] = FormInt()
        self.index['max_s_freq'] = FormInt()

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
        form_layout.addRow('Maximum Sampling Frequency',
                           self.index['max_s_freq'])

        box1 = QGroupBox('Grid')

        self.index['grid_x'] = FormBool('Grid on time axis')
        self.index['grid_xtick'] = FormFloat()
        self.index['grid_y'] = FormBool('Grid on voltage axis')
        self.index['grid_ytick'] = FormFloat()

        form_layout = QFormLayout()
        box1.setLayout(form_layout)
        form_layout.addRow(self.index['grid_x'])
        form_layout.addRow('Tick every (s)', self.index['grid_xtick'])
        form_layout.addRow(self.index['grid_y'])
        form_layout.addRow('Lines at + and - (uV):', self.index['grid_ytick'])

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
    idx_markers : list of QGraphicsRectItem
        list of markers in the dataset
    idx_annot : list of QGraphicsRectItem
        list of user-made annotations
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigTraces(self.parent.overview.update_position)

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
        self.idx_markers = []
        self.idx_annot = []
        self.idx_annot_labels = []
        self.cross_chan_mrk = True
        self.highlight = None
        self.event_sel = None
        self.current_event_row = None
        self.deselect = None
        self.ready = True

        self.create_action()

    def create_action(self):
        """Create actions associated with this widget."""
        actions = {}

        act = QAction(QIcon(ICON['step_prev']), 'Previous Step', self)
        act.setShortcut('[')
        act.triggered.connect(self.step_prev)
        actions['step_prev'] = act

        act = QAction(QIcon(ICON['step_next']), 'Next Step', self)
        act.setShortcut(']')
        act.triggered.connect(self.step_next)
        actions['step_next'] = act

        act = QAction(QIcon(ICON['page_prev']), 'Previous Page', self)
        act.setShortcut(QKeySequence.MoveToPreviousChar)
        act.triggered.connect(self.page_prev)
        actions['page_prev'] = act

        act = QAction(QIcon(ICON['page_next']), 'Next Page', self)
        act.setShortcut(QKeySequence.MoveToNextChar)
        act.triggered.connect(self.page_next)
        actions['page_next'] = act

        act = QAction('Go to Epoch', self)
        act.setShortcut(QKeySequence.FindNext)
        act.triggered.connect(self.go_to_epoch)
        actions['go_to_epoch'] = act

        act = QAction('Line Up with Epoch', self)
        act.triggered.connect(self.line_up_with_epoch)
        actions['line_up_with_epoch'] = act

        act = QAction(QIcon(ICON['zoomprev']), 'Wider Time Window', self)
        act.setShortcut(QKeySequence.ZoomIn)
        act.triggered.connect(self.X_more)
        actions['X_more'] = act

        act = QAction(QIcon(ICON['zoomnext']), 'Narrower Time Window', self)
        act.setShortcut(QKeySequence.ZoomOut)
        act.triggered.connect(self.X_less)
        actions['X_less'] = act

        act = QAction(QIcon(ICON['zoomin']), 'Larger Scaling', self)
        act.setShortcut(QKeySequence.MoveToPreviousLine)
        act.triggered.connect(self.Y_more)
        actions['Y_less'] = act

        act = QAction(QIcon(ICON['zoomout']), 'Smaller Scaling', self)
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

        act = QAction('Go to next event', self)
        act.setShortcut('s')
        act.triggered.connect(self.next_event)
        actions['next_event'] = act
        
        act = QAction('Delete event and go to next', self)
        act.setShortcut('d')
        act.triggered.connect(partial(self.next_event, True))
        actions['del_and_next_event'] = act
        
        act = QAction('Next event of same type', self)
        act.setCheckable(True)
        act.setChecked(True)
        actions['next_of_same_type'] = act
        
        act = QAction('Centre window around event', self)
        act.setCheckable(True)
        act.setChecked(True)
        actions['centre_event'] = act
        
        act = QAction('Full-length markers', self)
        act.setCheckable(True)
        act.setChecked(True)
        act.triggered.connect(self.display_annotations)
        actions['cross_chan_mrk'] = act

        # Misc
        act = QAction('Export to svg...', self)
        act.triggered.connect(partial(export_graphics, MAIN=self.parent))
        actions['export_svg'] = act

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

        max_s_freq = self.parent.value('max_s_freq')
        if data.s_freq > max_s_freq:
            q = int(data.s_freq / max_s_freq)
            lg.debug('Decimate (no low-pass filter) at ' + str(q))

            data.data[0] = data.data[0][:, slice(None, None, q)]
            data.axis['time'][0] = data.axis['time'][0][slice(None, None, q)]
            data.s_freq = int(data.s_freq / q)

        self.data = _create_data_to_plot(data, self.parent.channels.groups)


    def display(self):
        """Display the recordings."""
        if self.data is None:
            return

        if self.scene is not None:
            self.y_scrollbar_value = self.verticalScrollBar().value()
            self.scene.clear()

        self.create_chan_labels()
        self.create_time_labels()

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

        self.idx_markers = []
        self.idx_annot = []
        self.idx_annot_labels = []

        self.add_chan_labels()
        self.add_time_labels()
        self.add_traces()
        self.display_grid()
        self.display_markers()
        self.display_annotations()

        self.resizeEvent(None)
        self.verticalScrollBar().setValue(self.y_scrollbar_value)
        self.parent.info.display_view()
        self.parent.overview.display_current()

    def create_chan_labels(self):
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
                item.setBrush(QBrush(QColor(one_grp['color'])))
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                self.idx_label.append(item)

    def create_time_labels(self):
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

        self.idx_time = []
        self.time_pos = []
        for one_time in linspace(min_time, max_time, n_time_labels):
            x_label = (self.data.start_time +
                       timedelta(seconds=one_time)).strftime('%H:%M:%S')
            item = QGraphicsSimpleTextItem(x_label)
            item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            self.idx_time.append(item)
            self.time_pos.append(QPointF(one_time,
                                         len(self.idx_label) *
                                         self.parent.value('y_distance')))

    def add_chan_labels(self):
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
        y_distance = self.parent.value('y_distance')
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
                path.setPen(QPen(QColor(one_grp['color']), LINE_WIDTH))

                # adjust position
                chan_pos = y_distance * row + y_distance / 2
                path.setPos(0, chan_pos)
                row += 1

                self.chan.append(chan_name)
                self.chan_scale.append(one_grp['scale'])
                self.chan_pos.append(chan_pos)

    def display_grid(self):
        """Display grid on x-axis and y-axis."""
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
                path.setPen(QPen(QColor(LINE_COLOR), LINE_WIDTH,
                                 Qt.DotLine))

        if self.parent.value('grid_y'):
            y_tick = (self.parent.value('grid_ytick') *
                      self.parent.value('y_scale'))
            for one_label_item in self.idx_label:
                x_pos = [window_start, window_end]
                y = one_label_item.y()

                y_pos_0 = [y, y]
                path_0 = self.scene.addPath(Path(x_pos, y_pos_0))
                path_0.setPen(QPen(QColor(LINE_COLOR), LINE_WIDTH,
                                   Qt.DotLine))

                y_up = one_label_item.y() + y_tick
                y_pos_up = [y_up, y_up]
                path_up = self.scene.addPath(Path(x_pos, y_pos_up))
                path_up.setPen(QPen(QColor(LINE_COLOR), LINE_WIDTH,
                                    Qt.DotLine))

                y_down = one_label_item.y() - y_tick
                y_pos_down = [y_down, y_down]
                path_down = self.scene.addPath(Path(x_pos, y_pos_down))
                path_down.setPen(QPen(QColor(LINE_COLOR), LINE_WIDTH,
                                      Qt.DotLine))

    def display_markers(self):
        """Add markers on top of first plot."""
        for item in self.idx_markers:
            self.scene.removeItem(item)
        self.idx_markers = []

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        window_end = window_start + window_length
        y_distance = self.parent.value('y_distance')

        markers = []
        if self.parent.info.markers is not None:
            if self.parent.value('marker_show'):
                markers = self.parent.info.markers

        for mrk in markers:
            if window_start <= mrk['end'] and window_end >= mrk['start']:

                mrk_start = max((mrk['start'], window_start))
                mrk_end = min((mrk['end'], window_end))
                color = QColor(self.parent.value('marker_color'))

                item = QGraphicsRectItem(mrk_start, 0,
                                         mrk_end - mrk_start,
                                         len(self.idx_label) * y_distance)
                item.setPen(color)
                item.setBrush(color)
                item.setZValue(-9)
                self.scene.addItem(item)

                item = TextItem_with_BG(color.darker(200))
                item.setText(mrk['name'])
                item.setPos(mrk['start'],
                            len(self.idx_label) *
                            self.parent.value('y_distance'))
                item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                item.setRotation(-90)
                self.scene.addItem(item)
                self.idx_markers.append(item)

    def display_annotations(self):
        """Mark all the bookmarks/events, on top of first plot."""
        for item in self.idx_annot:
            self.scene.removeItem(item)
        self.idx_annot = []
        for item in self.idx_annot_labels:
            self.scene.removeItem(item)
        self.idx_annot_labels = []
        self.highlight = None

        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        window_end = window_start + window_length
        y_distance = self.parent.value('y_distance')

        bookmarks = []
        events = []

        if self.parent.notes.annot is not None:
            if self.parent.value('annot_show'):
                bookmarks = self.parent.notes.annot.get_bookmarks()
                events = self.parent.notes.get_selected_events((window_start,
                                                                window_end))
        annotations = bookmarks + events

        for annot in annotations:

            if window_start <= annot['end'] and window_end >= annot['start']:

                mrk_start = max((annot['start'], window_start))
                mrk_end = min((annot['end'], window_end))
                if annot in bookmarks:
                    color = QColor(self.parent.value('annot_bookmark_color'))
                if annot in events:
                    color = convert_name_to_color(annot['name'])

                if logical_or(annot['chan'] == [''],
                              self.action['cross_chan_mrk'].isChecked()):
                    h_annot = len(self.idx_label) * y_distance

                    item = TextItem_with_BG(color.darker(200))
                    item.setText(annot['name'])
                    item.setPos(annot['start'],
                                len(self.idx_label) * y_distance)
                    item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                    item.setRotation(-90)
                    self.scene.addItem(item)
                    self.idx_annot_labels.append(item)
                    mrk_dur = amax((mrk_end - mrk_start, 
                                  self.parent.value('min_marker_display_dur')))

                    item = RectMarker(mrk_start, 0, mrk_dur,
                                      h_annot, zvalue=-8,
                                      color=color.lighter(120))

                    self.scene.addItem(item)
                    self.idx_annot.append(item)

                if annot['chan'] != ['']:
                    # find indices of channels with annotations
                    chan_idx_in_mrk = in1d(self.chan, annot['chan'])
                    y_annot = asarray(self.chan_pos)[chan_idx_in_mrk]
                    y_annot -= y_distance / 2
                    mrk_dur = amax((mrk_end - mrk_start, 
                                  self.parent.value('min_marker_display_dur')))

                    for y in y_annot:
                        item = RectMarker(mrk_start, y, mrk_dur,
                                          y_distance, zvalue=-7, color=color)
                        self.scene.addItem(item)
                        self.idx_annot.append(item)

    def step_prev(self):
        """Go to the previous step."""
        window_start = around(self.parent.value('window_start') -
                              self.parent.value('window_length') /
                              self.parent.value('window_step'), 2)
        if window_start < 0:
            return
        self.parent.overview.update_position(window_start)

    def step_next(self):
        """Go to the next step."""
        window_start = around(self.parent.value('window_start') +
                              self.parent.value('window_length') /
                              self.parent.value('window_step'), 2)

        self.parent.overview.update_position(window_start)

    def page_prev(self):
        """Go to the previous page."""
        window_start = (self.parent.value('window_start') -
                        self.parent.value('window_length'))
        if window_start < 0:
            return
        self.parent.overview.update_position(window_start)

    def page_next(self):
        """Go to the next page."""
        window_start = (self.parent.value('window_start') +
                        self.parent.value('window_length'))
        self.parent.overview.update_position(window_start)

    def go_to_epoch(self, checked=False, test_text_str=None):
        """Go to any window"""
        if test_text_str is not None:
            time_str = test_text_str
            ok = True
        else:
            time_str, ok = QInputDialog.getText(self,
                                                'Go To Epoch',
                                                'Enter start time of the '
                                                'epoch,\nin seconds ("1560") '
                                                'or\nas absolute time '
                                                '("22:30")')

        if not ok:
            return

        try:
            rec_start_time = self.parent.info.dataset.header['start_time']
            window_start = _convert_timestr_to_seconds(time_str, rec_start_time)
        except ValueError as err:
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error moving to epoch')
            error_dialog.showMessage(str(err))
            if test_text_str is None:
                error_dialog.exec()
            self.parent.statusBar().showMessage(str(err))
            return

        self.parent.overview.update_position(window_start)

    def line_up_with_epoch(self):
        """Go to the start of the present epoch."""
        if self.parent.notes.annot is None:  # TODO: remove if buttons are disabled
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle('Error moving to epoch')
            error_dialog.showMessage('No score file loaded')
            error_dialog.exec()
            return

        new_window_start = self.parent.notes.annot.get_epoch_start(
            self.parent.value('window_start'))

        self.parent.overview.update_position(new_window_start)

    def add_time(self, extra_time):
        """Go to the predefined time forward."""
        window_start = self.parent.value('window_start') + extra_time
        self.parent.overview.update_position(window_start)

    def X_more(self):
        """Zoom in on the x-axis."""
        if self.parent.value('window_length') < 0.3:
            return
        self.parent.value('window_length',
                          self.parent.value('window_length') * 2)
        self.parent.overview.update_position()

    def X_less(self):
        """Zoom out on the x-axis."""
        self.parent.value('window_length',
                          self.parent.value('window_length') / 2)
        self.parent.overview.update_position()

    def X_length(self, new_window_length):
        """Use presets for length of the window."""
        self.parent.value('window_length', new_window_length)
        self.parent.overview.update_position()

    def Y_more(self):
        """Increase the scaling."""
        self.parent.value('y_scale', self.parent.value('y_scale') * 2)
        self.parent.traces.display()

    def Y_less(self):
        """Decrease the scaling."""
        self.parent.value('y_scale', self.parent.value('y_scale') / 2)
        self.parent.traces.display()

    def Y_ampl(self, new_y_scale):
        """Make scaling on Y axis using predefined values"""
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
        if not self.scene:
            return

        if self.event_sel:
            self.deselect = True
            self.event_sel = None
            self.current_event_row = None
            highlight = self.highlight
            self.scene.removeItem(highlight)
            self.highlight = None
            self.parent.statusBar().showMessage('')
            return

        self.ready = False
        self.event_sel = None

        xy_scene = self.mapToScene(event.pos())
        chan_idx = argmin(abs(asarray(self.chan_pos) - xy_scene.y()))
        self.sel_chan = chan_idx
        self.sel_xy = (xy_scene.x(), xy_scene.y())

        chk_marker = self.parent.notes.action['new_bookmark'].isChecked()
        chk_event = self.parent.notes.action['new_event'].isChecked()

        if not (chk_marker or chk_event):
            channame = self.chan[self.sel_chan] + ' in selected window'
            self.parent.spectrum.show_channame(channame)

        # JOB: Make annotations clickable
        else:
            for annot in self.idx_annot:
                if annot.contains(xy_scene):
                    self.highlight_event(annot)
                    row = self.parent.notes.find_row(annot.marker.x(),
                                    annot.marker.x() + annot.marker.width())
                    self.parent.notes.idx_annot_list.setCurrentCell(row, 0)
                    break

        # self.display_annotations
        self.ready = True

    def mouseMoveEvent(self, event):
        """When normal selection, update power spectrum with current selection.
        Otherwise, show the range of the new marker.
        """
        if not self.scene:
            return

        if self.event_sel or self.deselect:
            return

        if self.sel_xy[0] is None or self.sel_xy[1] is None:
            return

        if self.idx_sel in self.scene.items():
            self.scene.removeItem(self.idx_sel)
            self.idx_sel = None

        chk_marker = self.parent.notes.action['new_bookmark'].isChecked()
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
                color = QColor(self.parent.value('annot_bookmark_color'))

            elif chk_event:
                eventtype = self.parent.notes.idx_eventtype.currentText()
                color = convert_name_to_color(eventtype)

            item.setBrush(QBrush(color.lighter(115)))
            item.setZValue(-10)
            self.scene.addItem(item)
            self.idx_sel = item
            return

        xy_scene = self.mapToScene(event.pos())
        pos = QRectF(self.sel_xy[0], self.sel_xy[1],
                     xy_scene.x() - self.sel_xy[0],
                     xy_scene.y() - self.sel_xy[1])
        self.idx_sel = QGraphicsRectItem(pos.normalized())
        self.idx_sel.setPen(QPen(QColor(LINE_COLOR), LINE_WIDTH))
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
            data = pad(data, (int(ceil(n_pad)), int(floor(n_pad))), 'constant')

            self.parent.spectrum.display(data)

    def mouseReleaseEvent(self, event):
        """Create a new event or marker, or show the previous power spectrum
        """
        if not self.scene:
            return

        if self.event_sel:
            return

        if self.deselect:
            self.deselect = False
            return

        if not self.ready:
            return

        chk_marker = self.parent.notes.action['new_bookmark'].isChecked()
        chk_event = self.parent.notes.action['new_event'].isChecked()
        y_distance = self.parent.value('y_distance')

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
                    self.parent.notes.add_bookmark(time)

                elif chk_event and start != end:
                    eventtype = self.parent.notes.idx_eventtype.currentText()
                    chan_idx = int(floor(self.sel_xy[1] / y_distance))
                    chan = self.chan[chan_idx]
                    self.parent.notes.add_event(eventtype, time, chan)

        else:  # normal selection

            if self.idx_info in self.scene.items():
                self.scene.removeItem(self.idx_info)
            self.idx_info = None

            # restore spectrum
            self.parent.spectrum.update()
            self.parent.spectrum.display_window()

        # general garbage collection
        self.sel_chan = None
        self.sel_xy = (None, None)

        if self.idx_sel in self.scene.items():
            self.scene.removeItem(self.idx_sel)
            self.idx_sel = None

    def keyPressEvent(self, event):
        chk_event = self.parent.notes.action['new_event'].isChecked()
        if not (chk_event and self.event_sel):
            return

        annot = self.event_sel
        highlight = self.highlight
        annot_start = annot.marker.x()
        annot_end = annot_start + annot.marker.width()

        if type(event) == QKeyEvent and (
           event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace):
            self.parent.notes.remove_event(time=(annot_start, annot_end))
            self.scene.removeItem(highlight)
            msg = 'Deleted event from ' + str(annot_start) + ' to ' + str(annot_end)
            self.parent.statusBar().showMessage(msg)
            self.event_sel = None
            self.highlight = None
            self.display_annotations

    def highlight_event(self, annot):
        """Highlight an annotation on the trace.
        
        Parameters
        ----------
        annot : intance of wonambi.widgets.utils.RectMarker
            existing annotation
        """
        beg = annot.marker.x()
        end = beg + annot.marker.width()
        msg = 'Event from ' + str(beg) + ' to ' + str(end)
        self.parent.statusBar().showMessage(msg)
        highlight = RectMarker(annot.marker.x(),
                               annot.marker.y(),
                               annot.marker.width(),
                               annot.marker.height(),
                               zvalue=-5,
                               color=QColor(255, 255, 51))
        self.scene.addItem(highlight)
        self.highlight = highlight
        self.event_sel = annot
    
    def next_event(self, delete=False):
        """Go to next event."""
        if delete:
            msg = "Delete this event? This cannot be undone."
            msgbox = QMessageBox(QMessageBox.Question, 'Delete event', msg)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.Yes)
            response = msgbox.exec_()
            if response == QMessageBox.No:
                return
        
        event_sel = self.event_sel
        if event_sel is None:
            return
        
        notes = self.parent.notes
        
        if not self.current_event_row:
            row = notes.find_row(event_sel.marker.x(),
                            event_sel.marker.x() + event_sel.marker.width())
        else:
            row = self.current_event_row
            
        same_type = self.action['next_of_same_type'].isChecked()
        if same_type:
            target = notes.idx_annot_list.item(row, 2).text()
        
        if delete:            
            notes.delete_row()
            msg = 'Deleted event from {} to {}.'.format(event_sel.marker.x(), 
                            event_sel.marker.x() + event_sel.marker.width())
            self.parent.statusBar().showMessage(msg)
            row -= 1
        
        if row + 1 == notes.idx_annot_list.rowCount():
            return
        
        if not same_type:
            next_row = row + 1
        else:
            next_row = None
            types = notes.idx_annot_list.property('name')[row + 1:]
            
            for i, ty in enumerate(types):
                if ty == target:
                    next_row = row + 1 + i
                    break
                    
            if next_row is None:
                return                
                    
        self.current_event_row = next_row
        notes.go_to_marker(next_row, 0, 'annot')
        notes.idx_annot_list.setCurrentCell(next_row, 0)             
    
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
        data1 = montage(sel_data, ref_chan=one_grp['ref_chan'])

        data1.data[0] = nan_to_num(data1.data[0])

        if one_grp['hp'] is not None:
            data1 = filter_(data1, low_cut=one_grp['hp'])

        if one_grp['lp'] is not None:
            data1 = filter_(data1, high_cut=one_grp['lp'])

        for chan in one_grp['chan_to_plot']:
            chan_grp_name = chan + ' (' + one_grp['name'] + ')'
            all_chan_grp_name.append(chan_grp_name)

            dat = data1(chan=chan, trial=0)
            dat = dat - nanmean(dat)
            output.data[0][i_ch, :] = dat * one_grp['scale']
            i_ch += 1

    output.axis['chan'][0] = asarray(all_chan_grp_name, dtype='U')

    return output


def _convert_timestr_to_seconds(time_str, rec_start):
    """Convert input from user about time string to an absolute time for
    the recordings.

    Parameters
    ----------
    time_str : str
        time information as '123' or '22:30' or '22:30:22'
    rec_start: instance of datetime
        absolute start time of the recordings.

    Returns
    -------
    int
        start time of the window, in s, from the start of the recordings

    Raises
    ------
    ValueError
        if it cannot convert the string
    """
    if not CHECK_TIME_STR.match(time_str):
        raise ValueError('Input can only contain digits and colons')

    if ':' in time_str:
        time_split = [int(x) for x in time_str.split(':')]

        # if it's in 'HH:MM' format, add ':SS'
        if len(time_split) == 2:
            time_split.append(0)
        clock_time = time(*time_split)

        chosen_start = datetime.combine(rec_start.date(), clock_time)
        # if the clock time is after start of the recordings, assume it's the next day
        if clock_time < rec_start.time():
            chosen_start += timedelta(days=1)

        window_start = int((chosen_start - rec_start).total_seconds())
    else:
        window_start = int(time_str)

    return window_start
