"""Various functions used for the GUI.

"""
from logging import getLogger
lg = getLogger(__name__)

from math import ceil, floor

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import (QMessageBox,
                         QPainterPath,
                         QFormLayout,
                         QGroupBox,
                         QVBoxLayout,
                         )

from .settings import Config, FormInt, FormList, FormStr, FormFloat

MAX_LENGTH = 20

config = QSettings("phypno", "scroll_data")


class ConfigUtils(Config):

    def __init__(self, update_widget):
        super().__init__('utils', update_widget)

    def create_config(self):

        box0 = QGroupBox('Geometry')
        self.index['window_x'] = FormInt()
        self.index['window_y'] = FormInt()
        self.index['window_width'] = FormInt()
        self.index['window_height'] = FormInt()

        form_layout = QFormLayout()
        form_layout.addRow('Window X-position', self.index['window_x'])
        form_layout.addRow('Window Y-position', self.index['window_y'])
        form_layout.addRow('Window width', self.index['window_width'])
        form_layout.addRow('Window height', self.index['window_height'])

        box0.setLayout(form_layout)

        box1 = QGroupBox('History')
        self.index['max_recording_history'] = FormInt()
        self.index['recording_dir'] = FormStr()

        form_layout = QFormLayout()
        form_layout.addRow('Max History Size',
                           self.index['max_recording_history'])
        form_layout.addRow('Directory with recordings',
                           self.index['recording_dir'])
        box1.setLayout(form_layout)

        box2 = QGroupBox('Default values')
        self.index['y_distance_presets'] = FormList()  # require restart
        self.index['y_scale_presets'] = FormList()  # require restart
        self.index['window_length_presets'] = FormList()  # require restart

        form_layout = QFormLayout()
        form_layout.addRow('Signal scaling, presets',
                           self.index['y_scale_presets'])
        form_layout.addRow('Distance between signals, presets',
                           self.index['y_distance_presets'])
        form_layout.addRow('Window length, presets',
                           self.index['window_length_presets'])
        box2.setLayout(form_layout)

        box3 = QGroupBox('Download Data')
        self.index['read_intervals'] = FormFloat()

        form_layout = QFormLayout()
        form_layout.addRow('Read intervals (in s)',
                           self.index['read_intervals'])
        box3.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addWidget(box1)
        main_layout.addWidget(box2)
        main_layout.addWidget(box3)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


class Path(QPainterPath):

    def __init__(self, x, y):
        super().__init__()

        self.moveTo(x[0], y[0])
        for i_x, i_y in zip(x, y):
            self.lineTo(i_x, i_y)


def keep_recent_recordings(max_recording_history, new_recording=None):
    """Keep track of the most recent recordings.

    Parameters
    ----------
    new_recording : str, optional
        path to file
    max_recording_history : TODO

    Returns
    -------
    list of str
        paths to most recent recordings (only if you don't specify
        new_recording)

    """
    history = config.value('recent_recordings', [])
    if isinstance(history, str):
        history = [history]

    if new_recording is not None:
        if new_recording in history:
            lg.debug(new_recording + ' already present, will be replaced')
            history.remove(new_recording)
        if len(history) > max_recording_history:
            lg.debug('Removing last recording ' + history[-1])
            history.pop()

        lg.info('Adding ' + new_recording + ' to list of recent recordings')
        history.insert(0, new_recording)
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
