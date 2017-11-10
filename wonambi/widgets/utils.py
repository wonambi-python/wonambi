"""Various functions used for the GUI.
"""
from logging import getLogger
from math import ceil, floor
from os.path import dirname, join, realpath

from PyQt5.QtCore import QRectF, QSettings, Qt
from PyQt5.QtGui import (QBrush,
                         QColor,
                         QPainterPath,
                         )
from PyQt5.QtWidgets import (QGraphicsItem,
                             QGraphicsRectItem,
                             QGraphicsSimpleTextItem,
                             QMessageBox,
                             QCommonStyle,
                             )

lg = getLogger(__name__)

LINE_WIDTH = 0  # COSMETIC LINE
LINE_COLOR = 'black'


MAX_LENGTH = 20

stdicon = QCommonStyle.standardIcon


icon_path = join(dirname(realpath(__file__)), 'icons')
oxy_path = join(icon_path, 'oxygen')

ICON = {'open_rec': join(oxy_path, 'document-open.png'),
        'page_prev': join(oxy_path, 'go-previous-view.png'),
        'page_next': join(oxy_path, 'go-next-view.png'),
        'step_prev': join(oxy_path, 'go-previous.png'),
        'step_next': join(oxy_path, 'go-next.png'),
        'chronometer': join(oxy_path, 'chronometer.png'),
        'up': join(oxy_path, 'go-up.png'),
        'down': join(oxy_path, 'go-down.png'),
        'zoomin': join(oxy_path, 'zoom-in.png'),
        'zoomout': join(oxy_path, 'zoom-out.png'),
        'zoomnext': join(oxy_path, 'zoom-next.png'),
        'zoomprev': join(oxy_path, 'zoom-previous.png'),
        'ydist_more': join(oxy_path, 'format-line-spacing-triple.png'),
        'ydist_less': join(oxy_path, 'format-line-spacing-normal.png'),
        'selchan': join(oxy_path, 'mail-mark-task.png'),
        'widget': join(oxy_path, 'window-duplicate.png'),
        'settings': join(oxy_path, 'configure.png'),
        'quit': join(oxy_path, 'window-close.png'),
        'bookmark': join(oxy_path, 'bookmarks-organize.png'),
        'event': join(oxy_path, 'edit-table-cell-merge.png'),
        'new_eventtype': join(oxy_path, 'edit-table-insert-column-right.png'),
        'del_eventtype': join(oxy_path, 'edit-table-delete-column.png'),
        }

settings = QSettings("wonambi", "wonambi")


class Path(QPainterPath):
    """Paint a line in the simplest possible way.

    Parameters
    ----------
    x : ndarray or list
        x-coordinates
    y : ndarray or list
        y-coordinates
    """
    def __init__(self, x, y):
        super().__init__()

        self.moveTo(x[0], y[0])
        for i_x, i_y in zip(x, y):
            self.lineTo(i_x, i_y)


class RectMarker(QGraphicsRectItem):
    """Class to draw a rectangular, coloured item.

    Parameters
    ----------
    x : float
        x position in scene
    y : gloat
        y position in scene
    width : float
        length in seconds
    height : float
        height in scene units
    color : str or QColor, optional
        color of the rectangle
    """
    def __init__(self, x, y, width, height, zvalue, color='blue'):
        super().__init__()

        self.color = color
        self.setZValue(zvalue)
        buffer = 1
        self.marker = QRectF(x, y, width, height)
        self.b_rect = QRectF(x - buffer/2, y + buffer/2, width + buffer,
                             height + buffer)

    def boundingRect(self):
        return self.b_rect

    def paint(self, painter, option, widget):
        color = QColor(self.color)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.marker)
        super().paint(painter, option, widget)


class TextItem_with_BG(QGraphicsSimpleTextItem):
    """Class to draw text with dark background (easier to read).

    Parameters
    ----------
    bg_color : str or QColor, optional
        color to use as background
    """
    def __init__(self, bg_color='black'):
        super().__init__()

        self.bg_color = bg_color
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setBrush(QBrush(Qt.white))

    def paint(self, painter, option, widget):
        bg_color = QColor(self.bg_color)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.boundingRect())
        super().paint(painter, option, widget)


def keep_recent_datasets(max_dataset_history, info=None):
    """Keep track of the most recent recordings.

    Parameters
    ----------
    max_dataset_history : int
        maximum number of datasets to remember
    info : str, optional TODO
        path to file

    Returns
    -------
    list of str
        paths to most recent datasets (only if you don't specify
        new_dataset)
    """
    history = settings.value('recent_recordings', [])
    if isinstance(history, str):
        history = [history]

    if info is not None and info.filename is not None:
        if info.repo is not None:
            # this will parsed by self.info.open_dataset()
            new_dataset = info.filename + ' (' + info.repo + ')'
        else:
            new_dataset = info.filename

        if new_dataset in history:
            lg.debug(new_dataset + ' already present, will be replaced')
            history.remove(new_dataset)
        if len(history) > max_dataset_history:
            lg.debug('Removing last dataset ' + history[-1])
            history.pop()

        lg.debug('Adding ' + new_dataset + ' to list of recent datasets')
        history.insert(0, new_dataset)
        settings.setValue('recent_recordings', history)
        return None

    else:
        return history


def choose_file_or_dir():
    """Create a simple message box to see if the user wants to open dir or file

    Returns
    -------
    str
        'dir' or 'file' or 'ieegorg' or 'abort'

    """
    question = QMessageBox(QMessageBox.Information, 'Open Dataset',
                           'Do you want to open a file, a directory or a '
                           'remote ieeg.org dataset?')
    dir_button = question.addButton('Directory', QMessageBox.YesRole)
    file_button = question.addButton('File', QMessageBox.NoRole)
    remote_button = question.addButton('Remote Dataset', QMessageBox.NoRole)
    question.addButton(QMessageBox.Cancel)
    question.exec_()
    response = question.clickedButton()

    if response == dir_button:
        return 'dir'
    elif response == file_button:
        return 'file'
    elif response == remote_button:
        return 'remote'
    else:
        return 'abort'


def short_strings(s, max_length=MAX_LENGTH):
    if len(s) > max_length:
        max_length -= 3  # dots
        start = ceil(max_length / 2)
        end = -floor(max_length / 2)
        s = s[:start] + '...' + s[end:]
    return s


def convert_name_to_color(s):
    """Convert any string to an RGB color.

    Parameters
    ----------
    s : str
        string to convert
    selection : bool, optional
        if an event is being selected, it's lighter

    Returns
    -------
    instance of QColor
        one of the possible color

    Notes
    -----
    It takes any string and converts it to RGB color. The same string always
    returns the same color. The numbers are a bit arbitrary but not completely.
    h is the baseline color (keep it high to have brighter colors). Make sure
    that the max module + h is less than 256 (RGB limit).

    The number you multiply ord for is necessary to differentiate the letters
    (otherwise 'r' and 's' are too close to each other).
    """
    h = 100
    v = [5 * ord(x) for x in s]
    sum_mod = lambda x: sum(x) % 100
    color = QColor(sum_mod(v[::3]) + h, sum_mod(v[1::3]) + h,
                   sum_mod(v[2::3]) + h)
    return color
