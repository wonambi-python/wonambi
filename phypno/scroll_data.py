#!/usr/bin/env python3

from PyQt4.QtGui import QApplication

if __name__ == '__main__':
    try:
        app = QApplication([])
        standalone = True
    except RuntimeError:
        standalone = False

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

from os.path import dirname, basename, splitext
from types import MethodType

from numpy import arange
from PyQt4.QtCore import QSettings
from PyQt4.QtGui import (QFileDialog,
                         QInputDialog,
                         QMainWindow,
                         )

settings = QSettings("phypno", "scroll_data")

from phypno.widgets.creation import (create_menubar, create_toolbar,
                                     create_actions, create_widgets)
from phypno.widgets.utils import (keep_recent_recordings,
                                  choose_file_or_dir,
                                  ConfigUtils)


VERSION = 9


class MainWindow(QMainWindow):
    """Create an instance of the main window.

    Attributes
    ----------
    preferences : instance of phypno.widgets.Preferences

    idx_docks : dict
        pointers to dockwidgets, to show or hide them.

    notes : instance of phypno.widgets.Notes

    channels : instance of phypno.widgets.Channels

    detect : instance of phypno.widgets.Detect

    info : instance of phypno.widgets.Info

    overview : instance of phypno.widgets.Overview

    spectrum : instance of phypno.widgets.Spectrum

    traces : instance of phypno.widgets.Traces

    video : instance of phypno.widgets.Video

    action : dict
        names of all the actions to perform

    menu_window : instance of menuBar.menu
        menu about the windows (to know which ones are shown or hidden)

    """
    def __init__(self):
        super().__init__()

        self.config = ConfigUtils(self.update_mainwindow)

        self.idx_docks = {}
        self.notes = None
        self.channels = None
        self.detect = None
        self.info = None
        self.overview = None
        self.spectrum = None
        self.traces = None
        self.video = None
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

        self.setWindowTitle('PHYPNO v ' + str(VERSION))
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
        self.setGeometry(self.config.value['window_x'],
                         self.config.value['window_y'],
                         self.config.value['window_width'],
                         self.config.value['window_height'])

    def action_open_rec(self, recent=None):
        """Action: open a new dataset."""
        if self.info.dataset is not None:
            self.reset_dataset()

        if recent:
            filename = recent
        else:
            try:
                dir_name = dirname(self.info.filename)
            except (AttributeError, TypeError):
                dir_name = self.config.value['recording_dir']

            file_or_dir = choose_file_or_dir()
            if file_or_dir == 'dir':
                filename = QFileDialog.getExistingDirectory(self,
                                                            'Open directory',
                                                            dir_name)
            elif file_or_dir == 'file':
                filename = QFileDialog.getOpenFileName(self, 'Open file',
                                                       dir_name)
            elif file_or_dir == 'abort':
                return

            if filename == '':
                return

        self.statusBar().showMessage('Reading dataset: ' + basename(filename))
        self.info.update_info(filename)
        self.statusBar().showMessage('')
        self.overview.update_overview()
        self.channels.update_channels(self.info.dataset.header['chan_name'])
        try:
            pass
            # TODO self.markers.update_markers(self.info.dataset.header)
        except (KeyError, ValueError):
            lg.info('No notes/markers present in the header of the file')

    def reset_dataset(self):
        """Remove all the information from previous dataset before loading a
        new one.

        """
        # store current dataset
        max_recording_history = self.config.value['max_recording_history']
        keep_recent_recordings(max_recording_history, self.info.filename)

        # main
        if self.traces.scene is not None:
            self.traces.scene.clear()

        # spectrum
        self.spectrum.idx_chan.clear()
        if self.spectrum.scene is not None:
            self.spectrum.scene.clear()

    def action_download(self, length=None):
        """Start the download of the dataset."""
        dataset = self.info.dataset
        if length is None or length > self.overview.maximum:
            length = self.overview.maximum

        steps = arange(self.overview.config.value['window_start'],
                       self.overview.config.value['window_start'] + length,
                       self.config.value['read_intervals'])
        one_chan = dataset.header['chan_name'][0]
        for begtime, endtime in zip(steps[:-1], steps[1:]):
            dataset.read_data(chan=[one_chan],
                              begtime=begtime,
                              endtime=endtime)
            self.overview.mark_downloaded(begtime, endtime)

    def action_show_settings(self):
        """Open the Setting windows, after updating the values in GUI."""
        self.config.set_values()
        self.overview.config.set_values()
        self.traces.config.set_values()
        self.spectrum.config.set_values()
        self.notes.config.set_values()
        self.detect.config.set_values()
        self.video.config.set_values()
        self.settings.show()

    def action_step_prev(self):
        """Go to the previous step."""
        window_start = (self.overview.config.value['window_start'] -
                        self.overview.config.value['window_length'] /
                        self.overview.config.value['window_step'])
        self.overview.update_position(window_start)

    def action_step_next(self):
        """Go to the next step."""
        window_start = (self.overview.config.value['window_start'] +
                        self.overview.config.value['window_length'] /
                        self.overview.config.value['window_step'])
        self.overview.update_position(window_start)

    def action_page_prev(self):
        """Go to the previous page."""
        window_start = (self.overview.config.value['window_start'] -
                        self.overview.config.value['window_length'])
        self.overview.update_position(window_start)

    def action_page_next(self):
        """Go to the next page."""
        window_start = (self.overview.config.value['window_start'] +
                        self.overview.config.value['window_length'])
        self.overview.update_position(window_start)

    def action_add_time(self, extra_time):
        """Go to the predefined time forward."""
        window_start = self.overview.config.value['window_start'] + extra_time
        self.overview.update_position(window_start)

    def action_X_more(self):
        """Zoom in on the x-axis."""
        self.overview.config.value['window_length'] *= 2
        self.overview.update_position()

    def action_X_less(self):
        """Zoom out on the x-axis."""
        self.overview.config.value['window_length'] /= 2
        self.overview.update_position()

    def action_X_length(self, new_window_length):
        """Use presets for length of the window."""
        self.overview.config.value['window_length'] = new_window_length
        self.overview.update_position()

    def action_Y_more(self):
        """Increase the amplitude."""
        self.traces.config.value['y_scale'] *= 2
        self.traces.display_traces()

    def action_Y_less(self):
        """Decrease the amplitude."""
        self.traces.config.value['y_scale'] /= 2
        self.traces.display_traces()

    def action_Y_ampl(self, new_y_scale):
        """Make amplitude on Y axis using predefined values"""
        self.traces.config.value['y_scale'] = new_y_scale
        self.traces.display_traces()

    def action_Y_wider(self):
        """Increase the distance of the lines."""
        self.traces.config.value['y_distance'] *= 1.4
        self.traces.display_traces()

    def action_Y_tighter(self):
        """Decrease the distance of the lines."""
        self.traces.config.value['y_distance'] /= 1.4
        self.traces.display_traces()

    def action_Y_dist(self, new_y_distance):
        """Use preset values for the distance between lines."""
        self.traces.config.value['y_distance'] = new_y_distance
        self.traces.display_traces()

    def action_new_annot(self):
        """Action: create a new file for annotations.

        It should be gray-ed out when no dataset
        """
        if self.info.filename is None:
            self.statusBar().showMessage('No dataset loaded')
            return

        filename = splitext(self.info.filename)[0] + '_scores.xml'
        filename = QFileDialog.getSaveFileName(self, 'Create annotation file',
                                               filename,
                                               'Annotation File (*.xml)')
        if filename == '':
            return

        self.notes.update_notes(filename, True)

    def action_load_annot(self):
        """Action: load a file for annotations."""
        if self.info.filename is not None:
            filename = splitext(self.info.filename)[0] + '_scores.xml'
        else:
            filename = None
        filename = QFileDialog.getOpenFileName(self, 'Load annotation file',
                                               filename,
                                               'Annotation File (*.xml)')
        if filename == '':
            return

        self.notes.update_notes(filename, False)

    def action_select_rater(self, rater=False):
        """
        First argument, if not specified, is a bool/False:
        http://pyqt.sourceforge.net/Docs/PyQt4/qaction.html#triggered

        """
        if rater:
            self.notes.annot.get_rater(rater)

        else:
            answer = QInputDialog.getText(self, 'New Rater',
                                          'Enter rater\'s name')
            if answer[1]:
                self.notes.annot.add_rater(answer[0])
                self.create_menubar()  # refresh list ot raters

        self.notes.display_notes()

    def action_delete_rater(self):
        """
        First argument, if not specified, is a bool/False:
        http://pyqt.sourceforge.net/Docs/PyQt4/qaction.html#triggered

        """
        answer = QInputDialog.getText(self, 'Delete Rater',
                                      'Enter rater\'s name')
        if answer[1]:
            self.notes.annot.remove_rater(answer[0])

        self.notes.display_notes()
        self.create_menubar()  # refresh list ot raters

    def moveEvent(self, event):
        """Main window is already resized."""
        self.config.value['window_x'] = self.geometry().x()
        self.config.value['window_y'] = self.geometry().y()
        self.config.value['window_width'] = self.geometry().width()
        self.config.value['window_height'] = self.geometry().height()
        self.config.set_values()  # save the values in GUI

    def resizeEvent(self, event):
        """Main window is already resized."""
        self.config.value['window_x'] = self.geometry().x()
        self.config.value['window_y'] = self.geometry().y()
        self.config.value['window_width'] = self.geometry().width()
        self.config.value['window_height'] = self.geometry().height()
        self.config.set_values()  # save the values in GUI

    def closeEvent(self, event):
        """save the name of the last open dataset."""
        self.config.get_values()  # get geometry and store it in preferences

        max_recording_history = self.config.value['max_recording_history']
        keep_recent_recordings(max_recording_history, self.info.filename)

        settings.setValue('window/state', self.saveState(VERSION))

        event.accept()


if __name__ == '__main__':

    q = MainWindow()
    q.show()
    q.action_open_rec('/home/gio/tools/phypno/data/MGXX/eeg/raw/xltek/MGXX_eeg_xltek_sessA_d03_06_38_05')
    q.notes.update_notes('/home/gio/tools/phypno/data/MGXX/doc/scores/MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml', False)

    if standalone:
        app.exec_()
        app.deleteLater()  # so that it kills the figure in the right order
