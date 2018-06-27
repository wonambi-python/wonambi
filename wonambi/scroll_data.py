#!/usr/bin/env python3

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    raise ImportError('You need to install PyQt5 to run GUI')


from argparse import ArgumentParser
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG
from datetime import datetime
from types import MethodType

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.QtGui import QIcon

from . import __version__
from .widgets.creation import (create_menubar, create_toolbar,
                               create_actions, create_widgets)
from .widgets.settings import DEFAULTS
from .widgets.utils import keep_recent_datasets, ICON

now = datetime.now()

lg = getLogger('wonambi')


DESCRIPTION = """
    Package to analyze EEG, ECoG and other electrophysiology formats. It
    allows for visualization of the results and for a GUI that can be used to
    score sleep stages.
    """

settings = QSettings("wonambi", "wonambi")


class MainWindow(QMainWindow):
    """Create an instance of the main window.

    """
    def __init__(self):
        super().__init__()

        lg.info('WONAMBI v{}'.format(__version__))
        lg.debug('Reading settings from {}'.format(settings.fileName()))

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

    def show_merge_dialog(self):
        """Create the event merging dialog."""
        self.merge_dialog.update_event_types()
        self.merge_dialog.show()
        
    def show_export_events_dialog(self):
        """Create the events export dialog."""
        self.export_events_dialog.update()
        self.export_events_dialog.show()        

    def show_export_dataset_dialog(self):
        """Create the dataset export dialog."""
        self.export_dataset_dialog.update()
        self.export_dataset_dialog.show()

    def show_spindle_dialog(self):
        """Create the spindle detection dialog."""
        self.spindle_dialog.update_groups()
        self.spindle_dialog.update_cycles()
        self.spindle_dialog.show()

    def show_slow_wave_dialog(self):
        """Create the SW detection dialog."""
        self.slow_wave_dialog.update_groups()
        self.slow_wave_dialog.update_cycles()
        self.slow_wave_dialog.show()

    def show_event_analysis_dialog(self):
        """Create the event analysis dialog."""
        self.event_analysis_dialog.update_types()
        self.event_analysis_dialog.update_groups()
        self.event_analysis_dialog.update_cycles()
        self.event_analysis_dialog.show()

    def show_analysis_dialog(self):
        """Create the analysis dialog."""
        self.analysis_dialog.update_evt_types()
        self.analysis_dialog.update_groups()
        self.analysis_dialog.update_cycles()
        self.analysis_dialog.show()

    def show_plot_dialog(self):
        """Create the plot frame widget."""
        self.plot_dialog.show()

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
    app.setWindowIcon(QIcon(ICON['application']))

    parser = ArgumentParser(prog='wonambi',
                            description=DESCRIPTION)
    parser.add_argument('-v', '--version', action='store_true',
                        help='Return version')
    parser.add_argument('-l', '--log', default='info',
                        help='Logging level: info (default), debug')
    parser.add_argument('--reset', action='store_true',
                        help='Reset (clear) configuration file')
    parser.add_argument('--bids', action='store_true',
                        help='Read the information stored in the BIDS format')
    parser.add_argument('dataset', nargs='?',
                        help='full path to dataset to open')
    parser.add_argument('annot', nargs='?',
                        help='full path to annotations file to open')
    parser.add_argument('montage', nargs='?',
                        help='full path to montage file to open')

    args = parser.parse_args()

    DATE_FORMAT = '%H:%M:%S'
    if args.log[:1].lower() == 'i':
        lg.setLevel(INFO)
        FORMAT = '{asctime:<10}{message}'

    elif args.log[:1].lower() == 'd':
        lg.setLevel(DEBUG)
        FORMAT = '{asctime:<10}{levelname:<10}{filename:<40}(l. {lineno: 6d})/ {funcName:<40}: {message}'

    formatter = Formatter(fmt=FORMAT, datefmt=DATE_FORMAT, style='{')
    handler = StreamHandler()
    handler.setFormatter(formatter)

    lg.handlers = []
    lg.addHandler(handler)

    if args.reset:
        settings.clear()

    if args.version:
        lg.info('WONAMBI v{}'.format(__version__))

    else:
        q = MainWindow()
        q.show()

        if args.dataset:
            q.info.open_dataset(args.dataset, bids=args.bids)

        if args.annot:
            q.notes.update_notes(args.annot)

        if args.montage:
            q.channels.load_channels(test_name=args.montage)

        app.exec()
