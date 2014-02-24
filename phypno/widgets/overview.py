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
                          QGraphicsItem,
                          )

# bookmark
# event
# stage
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
        'stage': {'pos0': 45, 'pos1': 30, 'tip': 'Sleep Stage'},
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
    item : dict of RectItem, SimpleText
        all the items in the scene

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        preferences = self.parent.preferences.values
        self.window_start = int(preferences['overview/window_start'])
        self.window_length = int(preferences['overview/window_length'])
        self.minimum = None
        self.maximum = None

        self.scene = None
        self.item = {}

        self.create_overview()

    def create_overview(self):
        """Define the area of QGraphicsView."""
        lg.debug('Creating Overview widget')

        preferences = self.parent.preferences.values
        x_scale = 1 / float(preferences['stages/scoring_window'])
        lg.debug('Set scene x-scaling to {}'.format(x_scale))
        self.scale(x_scale, 1)
        self.setMinimumHeight(total_height + 30)

    def update_overview(self):
        """Read full duration and update maximum."""
        lg.debug('Updating Overview widget')

        header = self.parent.info.dataset.header
        maximum = header['n_samples'] / header['s_freq']  # in s
        self.minimum = 0
        self.maximum = maximum
        self.display_overview()

    def display_overview(self):
        """Updates the widgets, especially based on length of recordings."""
        lg.debug('Displaying Overview widget')

        lg.debug('GraphicsScene is between {}s and {}s'.format(self.minimum,
                                                               self.maximum))
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
            self.item[name] = QGraphicsRectItem(self.minimum, pos['pos0'],
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
        steps = int(preferences['overview/timestamp_steps'])
        transform, _ = self.transform().inverted()

        for t in range(first_hour, last_hour, steps):
            t_as_datetime = datetime.fromtimestamp(t)
            date_as_text = t_as_datetime.strftime('%H:%M')

            text = self.scene.addSimpleText(date_as_text)
            text.setFlag(QGraphicsItem.ItemIgnoresTransformations)

            # set xpos and adjust for text width
            xpos = (t_as_datetime - start_time).total_seconds()
            text_width = text.boundingRect().width() * transform.m11()
            text.setPos(xpos - text_width / 2, time_height)

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
            self.window_start = new_position
            self.item['current'].setPos(self.window_start, 0)
        else:
            lg.debug('Updating position at {}'.format(self.window_start))

        self.parent.traces.update_traces()
        self.parent.spectrum.update_spectrum()
        if self.parent.stages.scores is not None:
            self.parent.stages.set_combobox_index()

    def mark_bookmarks(self):
        """Mark all the bookmarks.

        Notes
        -----
        Bookmarks at the moment are only marked once, when the file is read.
        So, we plot them all at the same time. In the future, we might want to
        add bookmarks, so we need to re-write this function like mark_stage
        where you only add bookmarks as you need them.

        """
        bookmarks = self.parent.bookmarks.bookmarks
        for bm in bookmarks:
            self.scene.addLine(bm['time'], bars['bookmark']['pos0'],
                               bm['time'],
                               bars['bookmark']['pos0'] +
                               bars['bookmark']['pos1'])

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
        y_pos = bars['stage']['pos0']

        # sum of pos0 and pos1 should always be the same, but better be safe
        print('look for item at x={}, y={}'.format(start_time,
                                                   y_pos +
                                                   stages[stage_name]['pos0'] +
                                                   stages[stage_name]['pos1']))
        # the -1 is really important, otherwise we stay on the edge of the rect
        old_score = self.scene.itemAt(start_time + length / 2,
                                      y_pos +
                                      stages[stage_name]['pos0'] +
                                      stages[stage_name]['pos1'] - 1)

        # check we are not removing the black border
        if old_score is not None and old_score.pen() == Qt.NoPen:
            lg.debug('Removing old score at {}'.format(start_time))
            self.scene.removeItem(old_score)

        lg.debug('Adding score {} at {} s'.format(stage_name, start_time))
        rect = QGraphicsRectItem(start_time,
                                 y_pos + stages[stage_name]['pos0'],
                                 length,
                                 stages[stage_name]['pos1'])
        print('score at x={}-{}, y={}-{}'.format(start_time,
                                                 start_time + length,
                                                 y_pos +
                                                 stages[stage_name]['pos0'],
                                                 y_pos +
                                                 stages[stage_name]['pos0'] +
                                                 stages[stage_name]['pos1']))
        rect.setPen(Qt.NoPen)
        rect.setBrush(stages[stage_name]['color'])
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
                                   bars['available']['pos0'],
                                   end_value - start_value,
                                   bars['available']['pos1'])
        avail.stackBefore(self.item['available'])
        avail.setPen(Qt.NoPen)
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
        window_length = self.parent.overview.window_length
        window_start = int(floor(x_in_scene / window_length) * window_length)
        self.update_position(window_start)