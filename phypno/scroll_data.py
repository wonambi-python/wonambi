#!/usr/bin/env python3
VERSION = 9.4

""" ------ START APPLICATION ------ """
from PyQt4.QtGui import QApplication

if __name__ == '__main__':
    try:
        app = QApplication([])
        standalone = True
    except RuntimeError:
        standalone = False

""" ------ KEEP LOG ------ """
from logging import getLogger, DEBUG, StreamHandler, Formatter

lg = getLogger('phypno')  # when called by itself, __name__ is __main__
FORMAT = '%(asctime)s %(filename)s/%(funcName)s (%(levelname)s): %(message)s'
DATE_FORMAT = '%H:%M:%S'

formatter = Formatter(fmt=FORMAT, datefmt=DATE_FORMAT)
handler = StreamHandler()
handler.setFormatter(formatter)

lg.handlers = []
lg.addHandler(handler)

lg.setLevel(DEBUG)

""" ------ IMPORT ------ """
from types import MethodType

from numpy import arange
from PyQt4.QtCore import QSettings
from PyQt4.QtGui import QMainWindow

from phypno.widgets.creation import (create_menubar, create_toolbar,
                                     create_actions, create_widgets)
from phypno.widgets.settings import DEFAULTS
from phypno.widgets.utils import keep_recent_datasets

settings = QSettings("phypno", "scroll_data")


class MainWindow(QMainWindow):
    """Create an instance of the main window.

    """
    def __init__(self):
        super().__init__()

        self.info = None
        self.channels = None
        self.spectrum = None
        self.overview = None
        self.notes = None
        self.detect = None
        self.video = None
        self.traces = None
        self.settings = None

        self.action = {}  # actions was already taken
        self.menu_window = None

        # I prefer to have these functions in a separate module, for clarify
        self.create_widgets = MethodType(create_widgets, self)
        self.create_actions = MethodType(create_actions, self)
        self.create_menubar = MethodType(create_menubar, self)
        self.create_toolbar = MethodType(create_toolbar, self)

        self.create_widgets()
        self.create_actions()
        self.create_menubar()
        self.create_toolbar()

        self.statusBar()

        self.setWindowTitle('PHYPNO v' + str(VERSION))
        self.set_geometry()
        window_state = settings.value('window/state')
        if window_state is not None:
            self.restoreState(window_state, VERSION)
        self.show()

    def update_mainwindow(self):
        """Functions to re-run once settings have been changed."""
        lg.debug('Updating main window')
        self.set_geometry()
        create_menubar(self)

    def set_geometry(self):
        """Simply set the geometry of the main window."""
        self.setGeometry(self.value('window_x'),
                         self.value('window_y'),
                         self.value('window_width'),
                         self.value('window_height'))

    def value(self, parameter, new_value=None):
        """This function is a shortcut for any parameter. Instead of calling
        the widget, its config and its values, you can call directly the
        parameter.

        Parameters
        ----------
        parameter : str
            name of the parameter of interest
        new_value : str or float, optional
            new value for the parameter

        Returns
        -------
        str or float
            if you didn't specify new_value, it returns the current value.

        Notes
        -----
        It's important to maintain an organized dict in DEFAULTS which has to
        correspond to the values in the widgets, also the name of the widget.
        DEFAULTS is used like a look-up table.

        """
        for widget_name, values in DEFAULTS.items():
            if parameter in values.keys():
                widget = getattr(self, widget_name)
                if new_value is None:
                    return widget.config.value[parameter]
                else:
                    lg.debug('setting value {0} of {1} to {2}'
                             ''.format(parameter, widget_name, new_value))
                    widget.config.value[parameter] = new_value

    def reset(self):
        """Remove all the information from previous dataset before loading a
        new one.

        """
        # store current dataset
        max_dataset_history = self.value('max_dataset_history')
        keep_recent_datasets(max_dataset_history, self.info.filename)

        # overview
        if self.overview.scene is not None:
            self.overview.scene.clear()
            self.overview.scene = None

        self.traces.reset()
        self.info.reset()
        self.notes.reset()
        self.channels.reset()

        # spectrum
        self.spectrum.idx_chan.clear()
        if self.spectrum.scene is not None:
            self.spectrum.scene.clear()

    def action_download(self, length=None):
        """Start the download of the dataset."""
        dataset = self.info.dataset
        if length is None or length > self.overview.maximum:
            length = self.overview.maximum

        steps = arange(self.value('window_start'),
                       self.value('window_start') + length,
                       self.value('read_intervals'))
        one_chan = dataset.header['chan_name'][0]
        for begtime, endtime in zip(steps[:-1], steps[1:]):
            dataset.read_data(chan=[one_chan],
                              begtime=begtime,
                              endtime=endtime)
            self.overview.mark_downloaded(begtime, endtime)

    def action_show_settings(self):
        """Open the Setting windows, after updating the values in GUI.
        """
        self.settings.config.set_values()
        self.overview.config.set_values()
        self.traces.config.set_values()
        self.spectrum.config.set_values()
        self.notes.config.set_values()
        self.detect.config.set_values()
        self.video.config.set_values()
        self.settings.show()

    def action_step_prev(self):
        """Go to the previous step."""
        window_start = (self.value('window_start') -
                        self.value('window_length') /
                        self.value('window_step'))
        self.overview.update_position(window_start)

    def action_step_next(self):
        """Go to the next step."""
        window_start = (self.value('window_start') +
                        self.value('window_length') /
                        self.value('window_step'))
        self.overview.update_position(window_start)

    def action_page_prev(self):
        """Go to the previous page."""
        window_start = self.value('window_start') - self.value('window_length')
        self.overview.update_position(window_start)

    def action_page_next(self):
        """Go to the next page."""
        window_start = self.value('window_start') + self.value('window_length')
        self.overview.update_position(window_start)

    def action_add_time(self, extra_time):
        """Go to the predefined time forward."""
        window_start = self.value('window_start') + extra_time
        self.overview.update_position(window_start)

    def action_X_more(self):
        """Zoom in on the x-axis."""
        self.value('window_length', self.value('window_length') * 2)
        self.overview.update_position()

    def action_X_less(self):
        """Zoom out on the x-axis."""
        self.value('window_length', self.value('window_length') / 2)
        self.overview.update_position()

    def action_X_length(self, new_window_length):
        """Use presets for length of the window."""
        self.value('window_length', new_window_length)
        self.overview.update_position()

    def action_Y_more(self):
        """Increase the amplitude."""
        self.value('y_scale', self.value('y_scale') * 2)
        self.traces.display()

    def action_Y_less(self):
        """Decrease the amplitude."""
        self.value('y_scale', self.value('y_scale') / 2)
        self.traces.display()

    def action_Y_ampl(self, new_y_scale):
        """Make amplitude on Y axis using predefined values"""
        self.value('y_scale', new_y_scale)
        self.traces.display()

    def action_Y_wider(self):
        """Increase the distance of the lines."""
        self.value('y_distance', self.value('y_distance') * 1.4)
        self.traces.display()

    def action_Y_tighter(self):
        """Decrease the distance of the lines."""
        self.value('y_distance', self.value('y_distance') / 1.4)
        self.traces.display()

    def action_Y_dist(self, new_y_distance):
        """Use preset values for the distance between lines."""
        self.value('y_distance', new_y_distance)
        self.traces.display()

    def moveEvent(self, event):
        """Main window is already resized."""
        self.value('window_x', self.geometry().x())
        self.value('window_y', self.geometry().y())
        self.value('window_width', self.geometry().width())
        self.value('window_height', self.geometry().height())
        self.settings.config.set_values()  # save the values in GUI

    def resizeEvent(self, event):
        """Main window is already resized."""
        self.value('window_x', self.geometry().x())
        self.value('window_y', self.geometry().y())
        self.value('window_width', self.geometry().width())
        self.value('window_height', self.geometry().height())
        self.settings.config.set_values()  # save the values in GUI

    def closeEvent(self, event):
        """save the name of the last open dataset."""
        self.settings.config.get_values()  # store geometry for next use

        max_dataset_history = self.value('max_dataset_history')
        keep_recent_datasets(max_dataset_history, self.info.filename)

        settings.setValue('window/state', self.saveState(VERSION))

        event.accept()


if __name__ == '__main__':

    q = MainWindow()
    q.show()
    # q.info.open_dataset('/home/gio/tools/phypno/data/MGXX/eeg/raw/xltek/MGXX_eeg_xltek_sessA_d03_06_38_05')
    # q.notes.update_notes('/home/gio/tools/phypno/data/MGXX/doc/scores/MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml', False)

    if standalone:
        app.exec_()
        app.deleteLater()  # so that it kills the figure in the right order
