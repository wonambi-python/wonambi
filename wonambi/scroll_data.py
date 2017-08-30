#!/usr/bin/env python3

from PyQt5.QtWidgets import QApplication

from logging import getLogger, INFO, StreamHandler, Formatter

lg = getLogger('wonambi')
FORMAT = '%(asctime)s %(filename)s/%(funcName)s (%(levelname)s): %(message)s'
DATE_FORMAT = '%H:%M:%S'

formatter = Formatter(fmt=FORMAT, datefmt=DATE_FORMAT)
handler = StreamHandler()
handler.setFormatter(formatter)

lg.handlers = []
lg.addHandler(handler)

lg.setLevel(INFO)

from datetime import datetime
now = datetime.now()
from types import MethodType

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from . import __version__
from .widgets.creation import (create_menubar, create_toolbar,
                               create_actions, create_widgets)
from .widgets.settings import DEFAULTS
from .widgets.utils import keep_recent_datasets

settings = QSettings("wonambi", "wonambi")


class MainWindow(QMainWindow):
    """Create an instance of the main window.

    """
    def __init__(self):
        super().__init__()

        self.info = None
        self.labels = None
        self.channels = None
        self.spectrum = None
        self.overview = None
        self.notes = None
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
        self.setWindowTitle('WONAMBI v' + __version__)

        window_geometry = settings.value('window/geometry')
        if window_geometry is not None:
            self.restoreGeometry(window_geometry)
        window_state = settings.value('window/state')
        if window_state is not None:
            self.restoreState(window_state)

        self.show()

    def refresh(self):
        """Functions to re-run once settings have been changed."""
        self.create_menubar()

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

    def update(self):
        """Once you open a dataset, it activates all the widgets.
        """
        self.info.display_dataset()
        self.overview.update()
        self.labels.update(labels=self.info.dataset.header['chan_name'])
        self.channels.update()

        try:
            self.info.markers = self.info.dataset.read_markers()
        except FileNotFoundError:
            lg.info('No notes/markers present in the header of the file')
        else:
            self.notes.update_dataset_marker()

    def reset(self):
        """Remove all the information from previous dataset before loading a
        new dataset.
        """

        # store current dataset
        max_dataset_history = self.value('max_dataset_history')
        keep_recent_datasets(max_dataset_history, self.info)

        # reset all the widgets
        self.labels.reset()
        self.channels.reset()
        self.info.reset()
        self.notes.reset()
        self.overview.reset()
        self.spectrum.reset()
        self.traces.reset()

    def show_settings(self):
        """Open the Setting windows, after updating the values in GUI. """
        self.notes.config.put_values()
        self.overview.config.put_values()
        self.settings.config.put_values()
        self.spectrum.config.put_values()
        self.traces.config.put_values()
        self.video.config.put_values()

        self.settings.show()

    def about(self):
        s = ('<b>WONAMBI Version {version}</b><br />'
             '<p>You can download the latest version at '
             '<a href="https://github.com/wonambi-python/wonambi">'
             'https://github.com/wonambi-python/wonambi</a> '
             'or you can upgrade to the latest release with:'
             '</p><p>'
             '<code>pip install --upgrade wonambi</code>'
             '</p><p>'
             'Copyright &copy; 2013-{year} '
             '<a href="http://www.gpiantoni.com">Gio Piantoni</a>, '
             "Jordan O'Byrne"
             '</p><p>'
             'This program is free software: you can redistribute it '
             'and/or modify it under the terms of the GNU General Public '
             'License as published by the Free Software Foundation, either '
             'version 3 of the License, or (at your option) any later version.'
             '</p><p>'
             'This program is distributed in the hope that it will be useful, '
             'but WITHOUT ANY WARRANTY; without even the implied warranty of '
             'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the '
             'GNU General Public License for more details.'
             '</p><p>'
             'You should have received a copy of the GNU General Public '
             'License along with this program.  If not, see '
             '<a href="http://www.gnu.org/licenses/">'
             'http://www.gnu.org/licenses/</a>.'
             '</p><p>'
             'Other licenses available, contact the author'
             '</p>')
        QMessageBox.about(self, 'WONAMBI', s.format(version=__version__,
                                                    year=now.year))

    def closeEvent(self, event):
        """save the name of the last open dataset."""
        max_dataset_history = self.value('max_dataset_history')
        keep_recent_datasets(max_dataset_history, self.info)

        settings.setValue('window/geometry', self.saveGeometry())
        settings.setValue('window/state', self.saveState())

        event.accept()


app = None


def main():
    global app
    app = QApplication([])

    q = MainWindow()
    q.show()

    app.exec_()
