from logging import getLogger
lg = getLogger(__name__)

from datetime import datetime, timedelta

from numpy import floor
from PySide.QtCore import Qt
from PySide.QtGui import (QBrush,
                          QPen,
                          QGraphicsLineItem,
                          QGraphicsRectItem,
                          QGraphicsScene,
                          QGraphicsView,
                          )

# bookmark
# event
# state
# available
current_line_height = 10

stages = {'Wake': {'pos0': 5, 'pos1': 25, 'color': Qt.black},
          'REM': {'pos0': 10, 'pos1': 20, 'color': Qt.magenta},
          'NREM1': {'pos0': 15, 'pos1': 15, 'color': Qt.cyan},
          'NREM2': {'pos0': 20, 'pos1': 10, 'color': Qt.blue},
          'NREM3': {'pos0': 25, 'pos1': 5, 'color': Qt.darkBlue},
          'Unknown': {'pos0': 30, 'pos1': 0, 'color': Qt.NoBrush},
         }

bars = {'bookmark': {'pos0': 15, 'pos1': 10, 'tip': 'Bookmarks'},
        'event': {'pos0': 30, 'pos1': 10, 'tip': 'Events'},
        'state': {'pos0': 45, 'pos1': 30, 'tip': 'Brain State'},
        'available': {'pos0': 80, 'pos1': 10, 'tip': 'Available Recordings'},
        }
time_height = 92
total_height = 100


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
    item : dict
        all the items, to keep track of

    Notes
    -----
    TODO: maybe use minimum more often, don't assume it's zero

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        preferences = self.parent.preferences.values
        self.window_start = int(preferences['overview/window_start'])
        self.window_length = int(preferences['overview/window_length'])
        self.minimum = 0
        self.maximum = None
        self.scene = None

        self.item = {}
        self.setMinimumHeight(total_height + 30)
        self.scale(1 / float(preferences['stages/scoring_window']), 1)

    def update_overview(self):
        """Read full duration and update maximum."""
        header = self.parent.info.dataset.header
        maximum = header['n_samples'] / header['s_freq']  # in s
        self.maximum = maximum
        self.display_overview()

    def display_overview(self):
        """Updates the widgets, especially based on length of recordings."""
        self.scene = QGraphicsScene(self.minimum, 0,
                                    self.maximum,
                                    total_height)
        self.setScene(self.scene)

        self.item['current'] = QGraphicsLineItem(self.window_start, 0,
                                                 self.window_start,
                                                 current_line_height)
        self.item['current'].setPen(QPen(Qt.red))
        self.scene.addItem(self.item['current'])

        for name, pos in bars.items():
            self.item[name] = QGraphicsRectItem(0, pos['pos0'],
                                                self.maximum, pos['pos1'])
            self.item[name].setToolTip(pos['tip'])
            self.scene.addItem(self.item[name])

        self.add_timestamps()

    def add_timestamps(self):
        """Add timestamps at the bottom of the overview."""
        start_time_dataset = self.parent.info.dataset.header['start_time']
        start_time = start_time_dataset + timedelta(seconds=self.minimum)
        first_hour = int(datetime(start_time.year, start_time.month,
                                  start_time.day,
                                  start_time.hour + 1).timestamp())

        end_time = start_time_dataset + timedelta(seconds=self.maximum)
        last_hour = int(datetime(end_time.year, end_time.month,
                                 end_time.day,
                                 end_time.hour + 1).timestamp())

        preferences = self.parent.preferences.values
        ratio = float(preferences['stages/scoring_window'])
        steps = int(preferences['overview/window_step'])

        for t in range(first_hour, last_hour, steps):
            t_as_datetime = datetime.fromtimestamp(t)
            date_as_text = t_as_datetime.strftime('%H:%M')

            text = self.scene.addSimpleText(date_as_text)
            text.scale(ratio, 1)

            # set xpos and adjust for text width
            xpos = (t_as_datetime - start_time).total_seconds()
            text_width = text.boundingRect().width() * ratio
            text.setPos(xpos - text_width / 2, time_height)

    def update_position(self, new_position=None):
        """If value changes, call scroll functions."""
        if new_position is not None:
            self.window_start = new_position
            self.item['current'].setPos(self.window_start, 0)
        else:
            pass
            # self.window_start = self.scrollbar.value()
        self.parent.traces.update_traces()
        if self.parent.stages.scores is not None:
            self.parent.stages.set_combobox_index()

    def mark_bookmarks(self):
        bookmarks = self.parent.bookmarks.bookmarks
        for bm in bookmarks:
            self.scene.addLine(bm['time'], bars['bookmark']['pos0'],
                               bm['time'],
                               bars['bookmark']['pos0'] +
                               bars['bookmark']['pos1'])

    def color_stages(self):
        epochs = self.parent.stages.scores.get_epochs()
        y_pos = bars['state']['pos0']

        rect = []
        for epoch in epochs.values():
            rect.append(QGraphicsRectItem(epoch['start_time'],
                                          y_pos +
                                          stages[epoch['stage']]['pos0'],
                                          epoch['end_time'] -
                                          epoch['start_time'],
                                          stages[epoch['stage']]['pos1']))
            rect[-1].setPen(Qt.NoPen)
            rect[-1].setBrush(stages[epoch['stage']]['color'])
            self.scene.addItem(rect[-1])
        self.stages = rect

    def more_download(self, start_value, end_value):
        """Set the value of the progress bar.

        Parameters
        ----------

        """
        avail = self.scene.addRect(start_value,
                                   bars['available']['pos0'],
                                   end_value - start_value,
                                   bars['available']['pos1'])
        avail.stackBefore(self.item['available'])
        avail.setPen(Qt.NoPen)
        avail.setBrush(QBrush(Qt.green))

    def mousePressEvent(self, event):
        x_in_scene = self.mapToScene(event.pos()).x()
        window_length = self.parent.overview.window_length
        window_start = int(floor(x_in_scene / window_length) * window_length)
        self.update_position(window_start)
