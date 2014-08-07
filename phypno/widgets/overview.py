"""Wide widget giving an overview of the markers, events, and sleep scores.

xml_file = '/home/gio/recordings/MG60/doc/scores/MG60_eeg_xltek_sessA_d05_08_50_49_scores.xml'

from re import sub

with open(xml_file, 'r') as f:
    s = f.read()
s1 = sub('<marker><name>(.*?)</name><time>(.*?)</time></marker>',
         '<marker><marker_name>\g<1></marker_name><marker_start>\g<2></marker_start><marker_end>\g<2></marker_end><marker_chan/></marker>',
         s)
with open(xml_file, 'w') as f:
    f.write(s1)


"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import datetime, timedelta

from numpy import floor
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QBrush,
                         QColor,
                         QFormLayout,
                         QGraphicsItem,
                         QGraphicsLineItem,
                         QGraphicsRectItem,
                         QGraphicsScene,
                         QGraphicsView,
                         QGroupBox,
                         QPen,
                         QVBoxLayout,
                         )

from .settings import Config, FormInt

current_line_height = 10

NoPen = QPen()
NoPen.setStyle(Qt.NoPen)

NoBrush = QBrush()
NoBrush.setStyle(Qt.NoBrush)

STAGES = {'Wake': {'pos0': 5, 'pos1': 25, 'color': Qt.black},
          'Movement': {'pos0': 5, 'pos1': 25, 'color': Qt.darkGray},
          'REM': {'pos0': 10, 'pos1': 20, 'color': Qt.magenta},
          'NREM1': {'pos0': 15, 'pos1': 15, 'color': Qt.cyan},
          'NREM2': {'pos0': 20, 'pos1': 10, 'color': Qt.blue},
          'NREM3': {'pos0': 25, 'pos1': 5, 'color': Qt.darkBlue},
          'Undefined': {'pos0': 0, 'pos1': 30, 'color': Qt.gray},
          'Unknown': {'pos0': 30, 'pos1': 0, 'color': NoBrush},
          }

BARS = {'marker': {'pos0': 15, 'pos1': 10, 'tip': 'Markers'},
        'event': {'pos0': 30, 'pos1': 10, 'tip': 'Events'},
        'stage': {'pos0': 45, 'pos1': 30, 'tip': 'Sleep Stage'},
        'available': {'pos0': 80, 'pos1': 10, 'tip': 'Available Recordings'},
        }
TIME_HEIGHT = 92
TOTAL_HEIGHT = 100


class ConfigOverview(Config):

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
    window_start : int or float
        start time of the window being plotted (in s).
    window_length : int or float
        length of the window being plotted (in s).
    maximum : int or float
        maximum length of the window (in s).
    scene : instance of QGraphicsScene
        to keep track of the objects.
    idx_item : dict of RectItem, SimpleText
        all the items in the scene

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigOverview(self.display)

        self.minimum = None
        self.maximum = None
        self.start_time = None  # datetime, absolute start time

        self.scene = None
        self.idx_item = {}

        self.create()

    def create(self):
        """Define the area of QGraphicsView."""
        self.setMinimumHeight(TOTAL_HEIGHT + 30)

    def update(self):
        """Read full duration and update maximum."""
        if self.parent.info.dataset is not None:
            # read from the dataset, if available
            header = self.parent.info.dataset.header
            maximum = header['n_samples'] / header['s_freq']  # in s
            self.minimum = 0
            self.maximum = maximum
            self.start_time = self.parent.info.dataset.header['start_time']

        elif self.parent.notes.annot is not None:
            # read from annotations
            dataset = self.parent.notes.annot.dataset
            self.minimum = dataset['first_second']
            self.maximum = dataset['last_second']
            self.start_time = dataset['start_time']

        # make it time-zone unaware
        self.start_time = self.start_time.replace(tzinfo=None)

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

        item = QGraphicsLineItem(self.parent.value('window_start'),
                                 0,
                                 self.parent.value('window_start'),
                                 current_line_height)
        item.setPen(QPen(Qt.red))
        self.scene.addItem(item)
        self.idx_item['current'] = item

        for name, pos in BARS.items():
            item = QGraphicsRectItem(self.minimum, pos['pos0'],
                                     self.maximum, pos['pos1'])
            item.setToolTip(pos['tip'])
            self.scene.addItem(item)
            self.idx_item[name] = item

        self.add_timestamps()

        if self.parent.notes.annot is not None:
            self.parent.notes.display_notes()

    def add_timestamps(self):
        """Add timestamps at the bottom of the overview.

        TODO: to improve, don't rely on the hour

        """
        start_time = self.start_time + timedelta(seconds=self.minimum)
        first_hour = int((start_time.replace(minute=0, second=0,
                                             microsecond=0) +
                          timedelta(hours=1)).timestamp())

        end_time = self.start_time + timedelta(seconds=self.maximum)
        last_hour = int((end_time.replace(minute=0, second=0,
                                          microsecond=0) +
                         timedelta(hours=1)).timestamp())

        steps = self.parent.value('timestamp_steps')
        transform, _ = self.transform().inverted()

        for t in range(first_hour, last_hour, steps):
            t_as_datetime = datetime.fromtimestamp(t)
            date_as_text = t_as_datetime.strftime('%H:%M')

            text = self.scene.addSimpleText(date_as_text)
            text.setFlag(QGraphicsItem.ItemIgnoresTransformations)

            # set xpos and adjust for text width
            xpos = (t_as_datetime - start_time).total_seconds()
            text_width = text.boundingRect().width() * transform.m11()
            text.setPos(xpos - text_width / 2, TIME_HEIGHT)

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
            self.idx_item['current'].setPos(self.parent.value('window_start'),
                                            0)

            current_time = (self.start_time +
                            timedelta(seconds=new_position))
            msg = 'Current time: ' + current_time.strftime('%H:%M:%S')
            self.parent.statusBar().showMessage(msg)
        else:
            lg.debug('Updating position at {}'
                     ''.format(self.parent.value('window_start')))

        if self.parent.info.dataset is not None:
            self.parent.traces.read_data()
            self.parent.traces.display()
            self.parent.spectrum.display_window()

        if self.parent.notes.annot is not None:
            self.parent.notes.set_stage_index()

    def display_markers(self):
        """Mark all the markers, from annotations or from the dataset. """
        annot_markers = []
        if self.parent.notes.annot is not None:
            annot_markers = self.parent.notes.annot.get_markers()
            for mrk in annot_markers:  # TEMPORARY WORKAROUND
                mrk['time'] = mrk['start']

        dataset_markers = []
        if self.parent.notes.dataset_markers is not None:
            dataset_markers = self.parent.notes.dataset_markers

        markers = annot_markers + dataset_markers

        for mrk in markers:
            l = self.scene.addLine(mrk['time'], BARS['marker']['pos0'],
                                   mrk['time'],
                                   BARS['marker']['pos0'] +
                                   BARS['marker']['pos1'])

            if mrk in annot_markers:
                color = self.parent.value('annot_marker_color')
            if mrk in dataset_markers:
                color = self.parent.value('dataset_marker_color')
            l.setPen(QPen(QColor(color)))

    def display_events(self):
        """Mark all the events, from annotations. """
        # if event is too short, it does not appear in overview
        overview_scale = self.parent.value('overview_scale')

        if self.parent.notes.annot is not None:
            events = self.parent.notes.annot.get_events()
            for evt in events:
                length = evt['end'] - evt['start']
                if length < overview_scale:
                    length = overview_scale
                rect = QGraphicsRectItem(evt['start'],
                                         BARS['event']['pos0'],
                                         length,
                                         BARS['event']['pos1'])
                rect.setPen(NoPen)
                rect.setBrush(QBrush(Qt.black))  # TODO: depend on events
                self.scene.addItem(rect)

    def display_stages(self, start_time, length, stage_name):
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

        # the -1 is really important, otherwise we stay on the edge of the rect
        old_score = self.scene.itemAt(start_time + length / 2,
                                      y_pos +
                                      STAGES[stage_name]['pos0'] +
                                      STAGES[stage_name]['pos1'] - 1)

        # check we are not removing the black border
        if old_score is not None and old_score.pen() == NoPen:
            lg.debug('Removing old score at {}'.format(start_time))
            self.scene.removeItem(old_score)

        rect = QGraphicsRectItem(start_time,
                                 y_pos + STAGES[stage_name]['pos0'],
                                 length,
                                 STAGES[stage_name]['pos1'])
        rect.setPen(NoPen)
        rect.setBrush(STAGES[stage_name]['color'])
        self.scene.addItem(rect)

    def mark_downloaded(self, start_value, end_value):
        """Set the value of the progress bar.

        Parameters
        ----------
        start_value : int
            beginning of the window that was read.
        end_value : int
            end of the window that was read.

        """
        avail = self.scene.addRect(start_value,
                                   BARS['available']['pos0'],
                                   end_value - start_value,
                                   BARS['available']['pos1'])
        avail.stackBefore(self.idx_item['available'])
        avail.setPen(NoPen)
        avail.setBrush(QBrush(Qt.green))

    def mousePressEvent(self, event):
        """Jump to window when user clicks on overview.

        Parameters
        ----------
        event : instance of QtCore.QEvent
            it contains the position that was clicked.

        Notes
        -----
        This function overwrites Qt function, therefore the non-standard
        name. Argument also depends on Qt.

        """
        x_in_scene = self.mapToScene(event.pos()).x()
        window_length = self.parent.value('window_length')
        window_start = int(floor(x_in_scene / window_length) * window_length)
        self.update_position(window_start)

    def reset(self):
        if self.overview.scene is not None:
            self.overview.scene.clear()
        self.overview.scene = None
