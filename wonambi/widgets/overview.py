"""Wide widget giving an overview of the recordings with markers and
annotations (bookmarks, events, and sleep scores)
"""
from datetime import timedelta
from logging import getLogger
from math import ceil, floor

from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QBrush,
                         QColor,
                         QPen,
                         )
from PyQt5.QtWidgets import (QFormLayout,
                             QGraphicsItem,
                             QGraphicsRectItem,
                             QGraphicsScene,
                             QGraphicsView,
                             QGroupBox,
                             QVBoxLayout,
                             )

from .settings import Config
from .utils import convert_name_to_color, FormInt, LINE_WIDTH

lg = getLogger(__name__)

NoPen = QPen()
NoPen.setStyle(Qt.NoPen)

NoBrush = QBrush()
NoBrush.setStyle(Qt.NoBrush)

STAGES = {'Wake': {'pos0': 5, 'pos1': 25, 'color': Qt.black},
          'Movement': {'pos0': 5, 'pos1': 25, 'color': Qt.darkGray},
          'Artefact': {'pos0': 5, 'pos1': 25, 'color': Qt.darkGray},
          'REM': {'pos0': 10, 'pos1': 20, 'color': Qt.magenta},
          'NREM1': {'pos0': 15, 'pos1': 15, 'color': Qt.cyan},
          'NREM2': {'pos0': 20, 'pos1': 10, 'color': Qt.blue},
          'NREM3': {'pos0': 25, 'pos1': 5, 'color': Qt.darkBlue},
          'Undefined': {'pos0': 0, 'pos1': 30, 'color': Qt.gray},
          'Unknown': {'pos0': 30, 'pos1': 0, 'color': NoBrush},
          'cycle': {'pos0': 42, 'pos1': 43, 'color': Qt.darkRed}
          }

BARS = {'markers': {'pos0': 0, 'pos1': 10, 'tip': 'Markers in Dataset'},
        'quality': {'pos0': 15, 'pos1': 10, 'tip': 'Signal quality'},
        'annot': {'pos0': 30, 'pos1': 10,
                  'tip': 'Annotations (bookmarks and events)'},
        'stage': {'pos0': 45, 'pos1': 30, 'tip': 'Sleep Stage'},
        }
CURR = {'pos0': 0, 'pos1': 90}
TIME_HEIGHT = 92
TOTAL_HEIGHT = 100


class ConfigOverview(Config):
    """Widget with preferences in Settings window for Overview."""
    def __init__(self, update_widget):
        super().__init__('overview', update_widget)

    def create_config(self):

        box0 = QGroupBox('Overview')
        self.index['timestamp_steps'] = FormInt()
        self.index['overview_scale'] = FormInt()

        form_layout = QFormLayout()
        form_layout.addRow('Steps in overview (in s)',
                           self.index['timestamp_steps'])
        form_layout.addRow('One pixel corresponds to (s)',
                           self.index['overview_scale'])

        box0.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


class Overview(QGraphicsView):
    """Show an overview of data, such as hypnogram and data in memory.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    config : ConfigChannels
        preferences for this widget

    minimum : int or float
        start time of the recording, from the absolute time of start_time in s
    maximum : int or float
        length of the recordings in s
    start_time : datetime
        absolute start time of the recording

    scene : instance of QGraphicsScene
        to keep track of the objects
    idx_current : QGraphicsRectItem
        instance of the current time window
    idx_markers : list of QGraphicsRectItem
        list of markers in the dataset
    idx_annot : list of QGraphicsRectItem
        list of user-made annotations
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigOverview(self.update_settings)

        self.minimum = None
        self.maximum = None
        self.start_time = None  # datetime, absolute start time

        self.scene = None
        self.idx_current = None
        self.idx_markers = []
        self.idx_annot = []
        self.idx_poi = []

        self.setMinimumHeight(TOTAL_HEIGHT + 30)

    def update(self, reset=True):
        """Read full duration and update maximum.

        Parameters
        ----------
        reset: bool
            If True, current window start time is reset to 0.
        """
        if self.parent.info.dataset is not None:
            # read from the dataset, if available
            header = self.parent.info.dataset.header
            maximum = header['n_samples'] / header['s_freq']  # in s
            self.minimum = 0
            self.maximum = maximum
            self.start_time = self.parent.info.dataset.header['start_time']

        elif self.parent.notes.annot is not None:
            # read from annotations
            annot = self.parent.notes.annot
            self.minimum = annot.first_second
            self.maximum = annot.last_second
            self.start_time = annot.start_time

        # make it time-zone unaware
        self.start_time = self.start_time.replace(tzinfo=None)

        if reset:
            self.parent.value('window_start', 0)  # the only value that is reset

        self.display()

    def display(self):
        """Updates the widgets, especially based on length of recordings."""
        lg.debug('GraphicsScene is between {}s and {}s'.format(self.minimum,
                                                               self.maximum))

        x_scale = 1 / self.parent.value('overview_scale')
        lg.debug('Set scene x-scaling to {}'.format(x_scale))

        self.scale(1 / self.transform().m11(), 1)  # reset to 1
        self.scale(x_scale, 1)

        self.scene = QGraphicsScene(self.minimum, 0,
                                    self.maximum,
                                    TOTAL_HEIGHT)
        self.setScene(self.scene)

        # reset annotations
        self.idx_markers = []
        self.idx_annot = []

        self.display_current()

        for name, pos in BARS.items():
            item = QGraphicsRectItem(self.minimum, pos['pos0'],
                                     self.maximum, pos['pos1'])
            item.setToolTip(pos['tip'])
            self.scene.addItem(item)

        self.add_timestamps()

    def add_timestamps(self):
        """Add timestamps at the bottom of the overview."""
        transform, _ = self.transform().inverted()

        stamps = _make_timestamps(self.start_time, self.minimum, self.maximum,
                                  self.parent.value('timestamp_steps'))

        for stamp, xpos in zip(*stamps):
            text = self.scene.addSimpleText(stamp)
            text.setFlag(QGraphicsItem.ItemIgnoresTransformations)

            # set xpos and adjust for text width
            text_width = text.boundingRect().width() * transform.m11()
            text.setPos(xpos - text_width / 2, TIME_HEIGHT)

    def update_settings(self):
        """After changing the settings, we need to recreate the whole image."""
        self.display()
        self.display_markers()
        if self.parent.notes.annot is not None:
            self.parent.notes.display_notes()

    def update_position(self, new_position=None):
        """Update the cursor position and much more.

        Parameters
        ----------
        new_position : int or float
            new position in s, for plotting etc.

        Notes
        -----
        This is a central function. It updates the cursor, then updates
        the traces, the scores, and the power spectrum. In other words, this
        function is responsible for keep track of the changes every time
        the start time of the window changes.
        """
        if new_position is not None:
            lg.debug('Updating position to {}'.format(new_position))
            self.parent.value('window_start', new_position)
            self.idx_current.setPos(new_position, 0)

            current_time = (self.start_time +
                            timedelta(seconds=new_position))
            msg = 'Current time: ' + current_time.strftime('%H:%M:%S')
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)
        else:
            lg.debug('Updating position at {}'
                     ''.format(self.parent.value('window_start')))

        if self.parent.info.dataset is not None:
            self.parent.traces.read_data()
            if self.parent.traces.data is not None:
                self.parent.traces.display()
                self.parent.spectrum.display_window()

        if self.parent.notes.annot is not None:
            self.parent.notes.set_stage_index()
            self.parent.notes.set_quality_index()

        self.display_current()

    def display_current(self):
        """Create a rectangle showing the current window."""
        if self.idx_current in self.scene.items():
            self.scene.removeItem(self.idx_current)

        item = QGraphicsRectItem(0,
                                 CURR['pos0'],
                                 self.parent.value('window_length'),
                                 CURR['pos1'])
        # it's necessary to create rect first, and then move it
        item.setPos(self.parent.value('window_start'), 0)
        item.setPen(QPen(Qt.lightGray))
        item.setBrush(QBrush(Qt.lightGray))
        item.setZValue(-10)
        self.scene.addItem(item)
        self.idx_current = item

    def display_markers(self):
        """Mark all the markers, from the dataset.

        This function should be called only when we load the dataset or when
        we change the settings.
        """
        for rect in self.idx_markers:
            self.scene.removeItem(rect)
        self.idx_markers = []

        markers = []
        if self.parent.info.markers is not None:
            if self.parent.value('marker_show'):
                markers = self.parent.info.markers

        for mrk in markers:
            rect = QGraphicsRectItem(mrk['start'],
                                     BARS['markers']['pos0'],
                                     mrk['end'] - mrk['start'],
                                     BARS['markers']['pos1'])
            self.scene.addItem(rect)

            color = self.parent.value('marker_color')
            rect.setPen(QPen(QColor(color)))
            rect.setBrush(QBrush(QColor(color)))
            rect.setZValue(-5)
            self.idx_markers.append(rect)

    def display_annotations(self):
        """Mark all the bookmarks/events, from annotations.

        This function is similar to display_markers, but they are called at
        different stages (f.e. when loading annotations file), so we keep them
        separate
        """
        for rect in self.idx_annot:
            self.scene.removeItem(rect)
        self.idx_annot = []

        if self.parent.notes.annot is None:
            return

        bookmarks = []
        events = []
        if self.parent.value('annot_show'):
            bookmarks = self.parent.notes.annot.get_bookmarks()
            events = self.parent.notes.get_selected_events()

        annotations = bookmarks + events

        for annot in annotations:
            rect = QGraphicsRectItem(annot['start'],
                                     BARS['annot']['pos0'],
                                     annot['end'] - annot['start'],
                                     BARS['annot']['pos1'])
            self.scene.addItem(rect)

            if annot in bookmarks:
                color = self.parent.value('annot_bookmark_color')
            if annot in events:
                color = convert_name_to_color(annot['name'])

            rect.setPen(QPen(QColor(color), LINE_WIDTH))
            rect.setBrush(QBrush(QColor(color)))
            rect.setZValue(-5)
            self.idx_annot.append(rect)

        for epoch in self.parent.notes.annot.epochs:
            self.mark_stages(epoch['start'],
                             epoch['end'] - epoch['start'],
                             epoch['stage'])
            self.mark_quality(epoch['start'],
                              epoch['end'] - epoch['start'],
                              epoch['quality'])

        cycles = self.parent.notes.annot.rater.find('cycles')
        cyc_starts = [float(mrkr.text) for mrkr in cycles.findall('cyc_start')]
        cyc_ends = [float(mrkr.text) for mrkr in cycles.findall('cyc_end')]

        for mrkr in cyc_starts:
            self.mark_cycles(mrkr, 30) # TODO: better width solution
        for mrkr in cyc_ends:
            self.mark_cycles(mrkr, 30, end=True)

    def mark_stages(self, start_time, length, stage_name):
        """Mark stages, only add the new ones.

        Parameters
        ----------
        start_time : int
            start time in s of the epoch being scored.
        length : int
           duration in s of the epoch being scored.
        stage_name : str
            one of the stages defined in global stages.
        """
        y_pos = BARS['stage']['pos0']
        current_stage = STAGES.get(stage_name, STAGES['Unknown'])

        # the -1 is really important, otherwise we stay on the edge of the rect
        old_score = self.scene.itemAt(start_time + length / 2,
                                      y_pos +
                                      current_stage['pos0'] +
                                      current_stage['pos1'] - 1,
                                      self.transform())

        # check we are not removing the black border
        if old_score is not None and old_score.pen() == NoPen:
            lg.debug('Removing old score at {}'.format(start_time))
            self.scene.removeItem(old_score)
            self.idx_annot.remove(old_score)

        rect = QGraphicsRectItem(start_time,
                                 y_pos + current_stage['pos0'],
                                 length,
                                 current_stage['pos1'])
        rect.setPen(NoPen)
        rect.setBrush(current_stage['color'])
        self.scene.addItem(rect)
        self.idx_annot.append(rect)

    def mark_quality(self, start_time, length, qual_name):
        """Mark signal quality, only add the new ones.

        Parameters
        ----------
        start_time : int
            start time in s of the epoch being scored.
        length : int
           duration in s of the epoch being scored.
        qual_name : str
            one of the stages defined in global stages.
        """
        y_pos = BARS['quality']['pos0']
        height = 10

        # the -1 is really important, otherwise we stay on the edge of the rect
        old_score = self.scene.itemAt(start_time + length / 2,
                                      y_pos + height - 1,
                                      self.transform())

        # check we are not removing the black border
        if old_score is not None and old_score.pen() == NoPen:
            lg.debug('Removing old score at {}'.format(start_time))
            self.scene.removeItem(old_score)
            self.idx_annot.remove(old_score)

        if qual_name == 'Poor':
            rect = QGraphicsRectItem(start_time, y_pos, length, height)
            rect.setPen(NoPen)
            rect.setBrush(Qt.black)
            self.scene.addItem(rect)
            self.idx_annot.append(rect)

    def mark_cycles(self, start_time, length, end=False):
        """Mark cycle bound, only add the new one.

        Parameters
        ----------
        start_time: int
            start time in s of the bounding epoch
        length : int
           duration in s of the epoch being scored.
        end: bool
            If True, marker will be a cycle end marker; otherwise, it's start.
        """
        y_pos = STAGES['cycle']['pos0']
        height = STAGES['cycle']['pos1']
        color = STAGES['cycle']['color']

        # the -1 is really important, otherwise we stay on the edge of the rect
        old_rect = self.scene.itemAt(start_time + length / 2,
                                     y_pos + height - 1,
                                     self.transform())

        # check we are not removing the black border
        if old_rect is not None and old_rect.pen() == NoPen:
            lg.debug('Removing old score at {}'.format(start_time))
            self.scene.removeItem(old_rect)
            self.idx_annot.remove(old_rect)

        rect = QGraphicsRectItem(start_time, y_pos, length, height)
        rect.setPen(NoPen)
        rect.setBrush(color)
        self.scene.addItem(rect)
        self.idx_annot.append(rect)

        if end:
            start_time += length
            length = - length

        kink_hi = QGraphicsRectItem(start_time, y_pos, length * 5, 1)
        kink_hi.setPen(NoPen)
        kink_hi.setBrush(color)
        self.scene.addItem(kink_hi)
        self.idx_annot.append(kink_hi)

        kink_lo = QGraphicsRectItem(start_time, y_pos + height, length * 5, 1)
        kink_lo.setPen(NoPen)
        kink_lo.setBrush(color)
        self.scene.addItem(kink_lo)
        self.idx_annot.append(kink_lo)

    def mark_poi(self, times=None):
        """Mark selected signal, from list of start and end times.
        
        Parameters
        ----------
        times : list of tuple of float
            start and end times, in sec form rec start
        """
        y_pos = BARS['quality']['pos0']
        height = 5
        
        for rect in self.idx_poi:
            self.scene.removeItem(rect)
        self.idx_poi = []
        
        if not times:
            return
        
        for beg, end in times:
            rect = QGraphicsRectItem(beg, y_pos, end - beg, height)
            rect.setPen(NoPen)
            rect.setBrush(Qt.darkRed)
            self.scene.addItem(rect)
            self.idx_poi.append(rect)            
    
    def mousePressEvent(self, event):
        """Jump to window when user clicks on overview.

        Parameters
        ----------
        event : instance of QtCore.QEvent
            it contains the position that was clicked.
        """
        if self.scene is not None:
            x_in_scene = self.mapToScene(event.pos()).x()
            window_length = self.parent.value('window_length')
            window_start = int(floor(x_in_scene / window_length) *
                               window_length)
            if self.parent.notes.annot is not None:
                window_start = self.parent.notes.annot.get_epoch_start(
                        window_start)
            self.update_position(window_start)

    def reset(self):
        """Reset the widget, and clear the scene."""
        self.minimum = None
        self.maximum = None
        self.start_time = None  # datetime, absolute start time

        self.idx_current = None
        self.idx_markers = []
        self.idx_annot = []

        if self.scene is not None:
            self.scene.clear()
        self.scene = None


def _make_timestamps(start_time, minimum, maximum, steps):
    """Create timestamps on x-axis, every so often.

    Parameters
    ----------
    start_time : instance of datetime
        actual start time of the dataset
    minimum : int
        start time of the recording from start_time, in s
    maximum : int
        end time of the recording from start_time, in s
    steps : int
        how often you want a label, in s

    Returns
    -------
    dict
        where the key is the label and the value is the time point where the
        label should be placed.

    Notes
    -----
    This function takes care that labels are placed at the meaningful time, not
    at random values.
    """
    t0 = start_time + timedelta(seconds=minimum)
    t1 = start_time + timedelta(seconds=maximum)

    t0_midnight = t0.replace(hour=0, minute=0, second=0, microsecond=0)

    d0 = t0 - t0_midnight
    d1 = t1 - t0_midnight

    first_stamp = ceil(d0.total_seconds() / steps) * steps
    last_stamp = ceil(d1.total_seconds() / steps) * steps

    stamp_label = []
    stamp_time = []
    for stamp in range(first_stamp, last_stamp, steps):
        stamp_as_datetime = t0_midnight + timedelta(seconds=stamp)
        stamp_label.append(stamp_as_datetime.strftime('%H:%M'))
        stamp_time.append(stamp - d0.total_seconds())

    return stamp_label, stamp_time
