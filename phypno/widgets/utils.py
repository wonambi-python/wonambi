"""Various functions used for the GUI.

"""
from logging import getLogger
lg = getLogger(__name__)

from math import ceil, floor
from os.path import dirname, join, realpath

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import (QMessageBox,
                         QPainterPath,
                         QFormLayout,
                         QGroupBox,
                         QVBoxLayout,
                         )

from .settings import Config, FormInt, FormList, FormStr, FormFloat

MAX_LENGTH = 20

icon_path = join(dirname(realpath(__file__)), '..', '..', 'var', 'icons',
                 'oxygen')
ICON = {'open_rec': join(icon_path, 'document-open.png'),
        'page_prev': join(icon_path, 'go-previous-view.png'),
        'page_next': join(icon_path, 'go-next-view.png'),
        'step_prev': join(icon_path, 'go-previous.png'),
        'step_next': join(icon_path, 'go-next.png'),
        'chronometer': join(icon_path, 'chronometer.png'),
        'up': join(icon_path, 'go-up.png'),
        'down': join(icon_path, 'go-down.png'),
        'zoomin': join(icon_path, 'zoom-in.png'),
        'zoomout': join(icon_path, 'zoom-out.png'),
        'zoomnext': join(icon_path, 'zoom-next.png'),
        'zoomprev': join(icon_path, 'zoom-previous.png'),
        'ydist_more': join(icon_path, 'format-line-spacing-triple.png'),
        'ydist_less': join(icon_path, 'format-line-spacing-normal.png'),
        'selchan': join(icon_path, 'mail-mark-task.png'),
        'download': join(icon_path, 'download.png'),
        'widget': join(icon_path, 'window-duplicate.png'),
        'settings': join(icon_path, 'configure.png'),
        'quit': join(icon_path, 'window-close.png'),
        'marker': join(icon_path, 'bookmarks-organize.png'),
        'event': join(icon_path, 'edit-table-cell-merge.png'),
        'new_event_type': join(icon_path,
                               'edit-table-insert-column-right.png'),
        'del_event_type': join(icon_path, 'edit-table-delete-column.png'),
        }

config = QSettings("phypno", "scroll_data")


class Path(QPainterPath):

    def __init__(self, x, y):
        super().__init__()

        self.moveTo(x[0], y[0])
        for i_x, i_y in zip(x, y):
            self.lineTo(i_x, i_y)


def keep_recent_datasets(max_dataset_history, new_dataset=None):
    """Keep track of the most recent recordings.

    Parameters
    ----------
    new_dataset : str, optional
        path to file
    max_dataset_history : TODO

    Returns
    -------
    list of str
        paths to most recent datasets (only if you don't specify
        new_dataset)

    """
    history = config.value('recent_recordings', [])
    if isinstance(history, str):
        history = [history]

    if new_dataset is not None:
        if new_dataset in history:
            lg.debug(new_dataset + ' already present, will be replaced')
            history.remove(new_dataset)
        if len(history) > max_dataset_history:
            lg.debug('Removing last dataset ' + history[-1])
            history.pop()

        lg.info('Adding ' + new_dataset + ' to list of recent datasets')
        history.insert(0, new_dataset)
        config.setValue('recent_recordings', history)
        return None
    else:
        return history


def choose_file_or_dir():
    """Create a simple message box to see if the user wants to open dir or file

    Returns
    -------
    str
        'dir' or 'file' or 'abort'

    """
    question = QMessageBox(QMessageBox.Information, 'Open Dataset',
                           'Do you want to open a file or a directory?')
    dir_button = question.addButton('Directory', QMessageBox.YesRole)
    file_button = question.addButton('File', QMessageBox.NoRole)
    question.addButton(QMessageBox.Cancel)
    question.exec_()
    response = question.clickedButton()

    if response == dir_button:
        return 'dir'
    elif response == file_button:
        return 'file'
    else:
        return 'abort'


def short_strings(s, max_length=MAX_LENGTH):
    if len(s) > max_length:
        max_length -= 3  # dots
        start = ceil(max_length / 2)
        end = -floor(max_length / 2)
        s = s[:start] + '...' + s[end:]
    return s


