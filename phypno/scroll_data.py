#!/usr/bin/env python3
VERSION = 11.3

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
from PyQt4.QtGui import QMainWindow, QMessageBox

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

        window_geometry = settings.value('window/geometry')
        if window_geometry is not None:
            self.restoreGeometry(window_geometry)
        window_state = settings.value('window/state')
        if window_state is not None:
            self.restoreState(window_state, VERSION)

        self.show()

    def update(self):
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

    def reset(self):
        """Remove all the information from previous dataset before loading a
        new dataset."""

        # store current dataset
        max_dataset_history = self.value('max_dataset_history')
        keep_recent_datasets(max_dataset_history, self.info.filename)

        # reset all the widgets
        self.channels.reset()
        self.info.reset()
        self.notes.reset()
        self.overview.reset()
        self.spectrum.reset()
        self.traces.reset()

    def action_download(self, length=None):
        """Check if the dataset is available.

        Parameters
        ----------
        length : int, optional
            amount of data to download, in seconds
        """
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
        s = ('<b>PHYPNO Version {version}</b><br />'
             '<p>You can download the latest version at '
             '<a href="https://github.com/gpiantoni/phypno">'
             'https://github.com/gpiantoni/phypno</a>.'
             '</p><p>'
             'Copyright &copy; 2013-2014 '
             '<a href="http://www.gpiantoni.com">Gio Piantoni</a>'
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
             '</p>')
        QMessageBox.about(self, 'PHYPNO', s.format(version=VERSION))

    def closeEvent(self, event):
        """save the name of the last open dataset."""
        max_dataset_history = self.value('max_dataset_history')
        keep_recent_datasets(max_dataset_history, self.info.filename)

        settings.setValue('window/geometry', self.saveGeometry())
        settings.setValue('window/state', self.saveState(VERSION))

        event.accept()


if __name__ == '__main__':

    q = MainWindow()
    q.show()
    # q.info.open_dataset('/home/gio/tools/phypno/data/MGXX/eeg/raw/xltek/MGXX_eeg_xltek_sessA_d03_06_38_05')
    # q.notes.update_notes('/home/gio/tools/phypno/data/MGXX/doc/scores/MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml', False)
    # q.channels.load_channels('/home/gio/tools/phypno/data/MGXX/doc/elec/MGXX_eeg_xltek_sessA_d03_06_38_05_channels.json')

    if standalone:
        app.exec_()
        app.deleteLater()  # so that it kills the figure in the right order
