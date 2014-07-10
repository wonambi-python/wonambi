#!/usr/bin/env python3

from PyQt4.QtGui import QApplication

if __name__ == '__main__':
    try:
        app = QApplication([])
        standalone = True
    except RuntimeError:
        standalone = False

from logging import getLogger, DEBUG, INFO, StreamHandler, Formatter

lg = getLogger('phypno')  # when called by itself, __name__ is __main__
FORMAT = '%(asctime)s %(filename)s/%(funcName)s (%(levelname)s): %(message)s'
DATE_FORMAT = '%H:%M:%S'

formatter = Formatter(fmt=FORMAT, datefmt=DATE_FORMAT)
handler = StreamHandler()
handler.setFormatter(formatter)

lg.handlers = []
lg.addHandler(handler)

lg.setLevel(DEBUG)


from functools import partial
from os.path import dirname, basename, splitext

from numpy import arange
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QAction,
                         QFileDialog,
                         QIcon,
                         QKeySequence,
                         QMainWindow,
                         )
# change phypno.widgets into .widgets
from phypno.widgets import (DockWidget,
                            Bookmarks, Events, Stages,
                            Channels,
                            Detect,
                            Info,
                            Overview,
                            Preferences,
                            Spectrum,
                            Traces,
                            Video)
from phypno.widgets.preferences import REMOVEPreferences
from phypno.widgets.utils import (ICON, create_menubar, create_toolbar,
                                  keep_recent_recordings, choose_file_or_dir,
                                  ConfigUtils)


class MainWindow(QMainWindow):
    """Create an instance of the main window.

    Attributes
    ----------
    preferences : instance of phypno.widgets.Preferences

    idx_docks : dict
        pointers to dockwidgets, to show or hide them.

    bookmarks : instance of phypno.widgets.Bookmarks

    events : instance of phypno.widgets.Events

    stages : instance of phypno.widgets.Stages

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

        self.config = ConfigUtils(None)  # TODO: which function should we call here?
        self.preferences = REMOVEPreferences(self)  # TODO: remove this, use only to raise Preference window

        self.idx_docks = {}
        self.bookmarks = None
        self.events = None
        self.stages = None
        self.channels = None
        self.detect = None
        self.info = None
        self.overview = None
        self.spectrum = None
        self.traces = None
        self.video = None
        self.action = {}
        self.menu_window = None

        self.create_actions()
        create_menubar(self)
        create_toolbar(self)
        self.create_widgets()
        self.statusBar()

        self.setGeometry(self.config.value['window_x'],
                         self.config.value['window_y'],
                         self.config.value['window_width'],
                         self.config.value['window_height'])
        self.setWindowTitle('Scroll Data')
        self.show()

    def create_actions(self):
        """Create all the possible actions.

        """
        actions = {}
        actions['open_rec'] = QAction(QIcon(ICON['open_rec']),
                                      'Open Recording...', self)
        actions['open_rec'].setShortcut(QKeySequence.Open)
        actions['open_rec'].triggered.connect(self.action_open_rec)

        recent_recs = keep_recent_recordings()
        actions['recent_rec'] = []
        for one_recent_rec in recent_recs:
            action_recent = QAction(one_recent_rec, self)
            action_recent.triggered.connect(partial(self.action_open_rec,
                                                    one_recent_rec))
            actions['recent_rec'].append(action_recent)

        actions['open_bookmarks'] = QAction('Open Bookmark File...', self)
        actions['open_events'] = QAction('Open Events File...', self)
        actions['open_stages'] = QAction('Open Stages File...', self)
        actions['open_stages'].triggered.connect(self.action_open_stages)

        actions['open_preferences'] = QAction(QIcon(ICON['preferences']),
                                              'Preferences', self)
        actions['open_preferences'].triggered.connect(self.open_preferences)
        actions['close_wndw'] = QAction(QIcon(ICON['quit']), 'Quit', self)
        actions['close_wndw'].triggered.connect(self.close)

        actions['step_prev'] = QAction(QIcon(ICON['step_prev']),
                                       'Previous Step', self)
        actions['step_prev'].setShortcut(QKeySequence.MoveToPreviousChar)
        actions['step_prev'].triggered.connect(self.action_step_prev)

        actions['step_next'] = QAction(QIcon(ICON['step_next']),
                                       'Next Step', self)
        actions['step_next'].setShortcut(QKeySequence.MoveToNextChar)
        actions['step_next'].triggered.connect(self.action_step_next)

        actions['page_prev'] = QAction(QIcon(ICON['page_prev']),
                                       'Previous Page', self)
        actions['page_prev'].setShortcut(QKeySequence.MoveToPreviousPage)
        actions['page_prev'].triggered.connect(self.action_page_prev)

        actions['page_next'] = QAction(QIcon(ICON['page_next']),
                                       'Next Page', self)
        actions['page_next'].setShortcut(QKeySequence.MoveToNextPage)
        actions['page_next'].triggered.connect(self.action_page_next)

        actions['X_more'] = QAction(QIcon(ICON['zoomprev']),
                                    'Wider Time Window', self)
        actions['X_more'].setShortcut(QKeySequence.ZoomIn)
        actions['X_more'].triggered.connect(self.action_X_more)

        actions['X_less'] = QAction(QIcon(ICON['zoomnext']),
                                    'Narrower Time Window', self)
        actions['X_less'].setShortcut(QKeySequence.ZoomOut)
        actions['X_less'].triggered.connect(self.action_X_less)

        actions['Y_less'] = QAction(QIcon(ICON['zoomin']),
                                    'Larger Amplitude', self)
        actions['Y_less'].setShortcut(QKeySequence.MoveToPreviousLine)
        actions['Y_less'].triggered.connect(self.action_Y_more)

        actions['Y_more'] = QAction(QIcon(ICON['zoomout']),
                                    'Smaller Amplitude', self)
        actions['Y_more'].setShortcut(QKeySequence.MoveToNextLine)
        actions['Y_more'].triggered.connect(self.action_Y_less)

        actions['Y_wider'] = QAction(QIcon(ICON['ydist_more']),
                                     'Larger Y Distance', self)
        actions['Y_wider'].triggered.connect(self.action_Y_wider)

        actions['Y_tighter'] = QAction(QIcon(ICON['ydist_less']),
                                       'Smaller Y Distance', self)
        actions['Y_tighter'].triggered.connect(self.action_Y_tighter)

        self.action = actions  # actions was already taken

    def action_open_rec(self, recent=None):
        """Action: open a new dataset.

        Notes
        -----
        I do not know how to run tests for QFileDialog.

        """
        if recent:
            filename = recent
        else:
            try:
                dir_name = dirname(self.info.filename)
            except (AttributeError, TypeError):
                dir_name = self.preferences.values['main/recording_dir']

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
            self.bookmarks.update_bookmarks(self.info.dataset.header)
        except (KeyError, ValueError):
            lg.info('No notes/bookmarks present in the header of the file')

    def action_open_stages(self):
        """Action: open a new file for sleep staging.

        Notes
        -----
        I do not know how to run tests for QFileDialog.

        """
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        try:
            filename = self.stages.scores.xml_file
        except AttributeError:
            filename = splitext(self.info.filename)[0] + '_scores.xml'
        filename = dialog.getOpenFileName(self, 'Open sleep score file',
                                          filename)
        if filename[0] == '':
            return
        self.stages.update_stages(filename)

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

    def create_widgets(self):
        """Create all the widgets and dockwidgets.

        Notes
        -----
        I tried to be consistent and use lambda for connect, but somehow
        partial works well while lambda passes always the same argument.

        """
        self.info = Info(self)
        self.channels = Channels(self)
        self.spectrum = Spectrum(self)
        self.overview = Overview(self)
        self.bookmarks = Bookmarks(self)
        self.events = Events(self)
        self.stages = Stages(self)
        self.detect = Detect(self)
        self.video = Video(self)
        self.traces = Traces(self)
        self.settings = Preferences(self)

        self.setCentralWidget(self.traces)

        new_docks = [{'name': 'Information',
                      'widget': self.info,
                      'main_area': Qt.LeftDockWidgetArea,
                      'extra_area': Qt.RightDockWidgetArea,
                      },
                     {'name': 'Channels',
                      'widget': self.channels,
                      'main_area': Qt.RightDockWidgetArea,
                      'extra_area': Qt.LeftDockWidgetArea,
                      },
                     {'name': 'Spectrum',
                      'widget': self.spectrum,
                      'main_area': Qt.RightDockWidgetArea,
                      'extra_area': Qt.LeftDockWidgetArea,
                      },
                     {'name': 'Bookmarks',
                      'widget': self.bookmarks,
                      'main_area': Qt.LeftDockWidgetArea,
                      'extra_area': Qt.RightDockWidgetArea,
                      },
                     {'name': 'Events',
                      'widget': self.events,
                      'main_area': Qt.LeftDockWidgetArea,
                      'extra_area': Qt.RightDockWidgetArea,
                      },
                     {'name': 'Stages',
                      'widget': self.stages,
                      'main_area': Qt.LeftDockWidgetArea,
                      'extra_area': Qt.RightDockWidgetArea,
                      },
                     {'name': 'Detect',
                      'widget': self.detect,
                      'main_area': Qt.LeftDockWidgetArea,
                      'extra_area': Qt.RightDockWidgetArea,
                      },
                     {'name': 'Video',
                      'widget': self.video,
                      'main_area': Qt.LeftDockWidgetArea,
                      'extra_area': Qt.RightDockWidgetArea,
                      },
                     {'name': 'Overview',
                      'widget': self.overview,
                      'main_area': Qt.BottomDockWidgetArea,
                      'extra_area': Qt.TopDockWidgetArea,
                      },
                     ]

        self.idx_docks = {}
        actions = self.action
        for dock in new_docks:
            self.idx_docks[dock['name']] = DockWidget(self,
                                                      dock['name'],
                                                      dock['widget'],
                                                      dock['main_area'] |
                                                      dock['extra_area'])
            self.addDockWidget(dock['main_area'], self.idx_docks[dock['name']])
            new_act = QAction(QIcon(ICON['widget']), dock['name'], self)
            new_act.setCheckable(True)
            new_act.setChecked(True)
            new_act.triggered.connect(partial(self.toggle_menu_window,
                                              dock['name'],
                                              self.idx_docks[dock['name']]))
            self.menu_window.addAction(new_act)
            actions[dock['name']] = new_act

            if dock['name'] in self.preferences.values['main/hidden_docks']:
                self.idx_docks[dock['name']].setVisible(False)
                actions[dock['name']].setChecked(False)

        self.tabifyDockWidget(self.idx_docks['Information'],
                              self.idx_docks['Video'])
        self.idx_docks['Information'].raise_()

        self.tabifyDockWidget(self.idx_docks['Bookmarks'],
                              self.idx_docks['Events'])
        self.tabifyDockWidget(self.idx_docks['Events'],
                              self.idx_docks['Stages'])
        self.tabifyDockWidget(self.idx_docks['Stages'],
                              self.idx_docks['Detect'])
        self.idx_docks['Bookmarks'].raise_()

    def toggle_menu_window(self, dockname, dockwidget):
        """Show or hide dockwidgets, and keep track of them.

        Parameters
        ----------
        dockname : str
            name of the dockwidget
        dockwidget : instance of DockWidget

        """
        actions = self.action
        if dockwidget.isVisible():
            dockwidget.setVisible(False)
            actions[dockname].setChecked(False)
            lg.debug('Setting ' + dockname + ' to invisible')
        else:
            dockwidget.setVisible(True)
            dockwidget.raise_()
            actions[dockname].setChecked(True)
            lg.debug('Setting ' + dockname + ' to visible')

    def open_preferences(self):
        self.settings.update_preferences()
        self.settings.show()

    def closeEvent(self, event):
        """save the name of the last open dataset."""
        keep_recent_recordings(self.info.filename)
        event.accept()


if __name__ == '__main__':

    q = MainWindow()
    q.show()

    if standalone:
        app.exec_()
