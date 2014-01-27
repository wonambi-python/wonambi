from logging import getLogger, INFO
lg = getLogger(__name__)
lg.setLevel(INFO)

from os.path import dirname
from sys import argv, exit
from PySide.QtCore import Qt, QSettings, QThread
from PySide.QtGui import (QAction,
                          QApplication,
                          QFileDialog,
                          QIcon,
                          QKeySequence,
                          QMainWindow,
                          )
from pyqtgraph import setConfigOption
# change phypno.widgets into .widgets
from phypno.widgets import (Info, Channels, Overview, Scroll, Stages, Video,
                            DownloadData, DockWidget)

from functools import partial

icon = {
    'open_rec': QIcon.fromTheme('document-open'),
    'page_prev': QIcon.fromTheme('go-previous-view'),
    'page_next': QIcon.fromTheme('go-next-view'),
    'step_prev': QIcon.fromTheme('go-previous'),
    'step_next': QIcon.fromTheme('go-next'),
    'cronometer': QIcon.fromTheme('cronometer'),
    'up': QIcon.fromTheme('go-up'),
    'down': QIcon.fromTheme('go-down'),
    'zoomin': QIcon.fromTheme('zoom-in'),
    'zoomout': QIcon.fromTheme('zoom-out'),
    'zoomnext': QIcon.fromTheme('zoom-next'),
    'zoomprev': QIcon.fromTheme('zoom-previous'),
    'selchan': QIcon.fromTheme('mail-mark-task'),
    'download': QIcon.fromTheme('download'),
    'widget': QIcon.fromTheme('window-duplicate'),
    }

DATASET_EXAMPLE = ('/home/gio/recordings/MG71/eeg/raw/' +
                   'MG71_eeg_sessA_d01_21_17_40')
DATASET_EXAMPLE = '/home/gio/tools/phypno/test/data/sample.edf'
# DATASET_EXAMPLE = '/home/gio/Copy/presentations_x/video/VideoFileFormat_1'
# DATASET_EXAMPLE = '/home/gio/ieeg/data/MG63_d2_Thurs_d.edf'
# DATASET_EXAMPLE = '/home/gio/tools/phypno/test/data/MG71_d1_Wed_c.edf'

setConfigOption('background', 'w')

config = QSettings("phypno", "scroll_data")
config.setValue('window_start', 0)
config.setValue('window_page_length', 30)
# one step = window_page_length / window_step_ratio
config.setValue('window_step_ratio', 5)
config.setValue('ylimit', 100)
config.setValue('read_intervals', 60)  # pre-read file every X seconds
config.setValue('hidden_docks', ['Video', ])
config.setValue('ratio_second_overview', 60)  # one pixel per 60 s


class MainWindow(QMainWindow):
    """Create an instance of the main window.

    Attributes
    ----------
    action : dict
        names of all the actions to perform
    info : instance of phypno.widgets.Info

    channels : instance of phypno.widgets.Channels

    overview : instance of phypno.widgets.Overview

    video : instance of phypno.widgets.Video

    scroll : instance of phypno.widgets.Scroll

    docks : dict
        pointers to dockwidgets, to show or hide them.
    menu_window : instance of menuBar.menu
        menu about the windows (to know which ones are shown or hidden)
    thread_download : instance of QThread
        necessary to avoid garbage collection.

    """
    def __init__(self):
        super().__init__()

        self.action = {}

        self.info = None
        self.channels = None
        self.overview = None
        self.scroll = None
        self.video = None
        self.docks = {}
        self.menu_window = None

        self.thread_download = None

        self.create_actions()
        self.create_menubar()
        self.create_toolbar()
        self.create_widgets()

        self.setGeometry(400, 300, 800, 600)
        self.setWindowTitle('Scroll Data')
        self.show()

    def create_actions(self):
        """Create all the possible actions.

        """
        actions = {}
        actions['open_rec'] = QAction(icon['open_rec'], 'Open Recording...',
                                      self)
        actions['open_rec'].setShortcut(QKeySequence.Open)
        actions['open_rec'].triggered.connect(self.action_open)

        actions['open_bookmark'] = QAction('Open Bookmark File...', self)
        actions['open_event'] = QAction('Open Events File...', self)
        actions['open_state'] = QAction('Open Stages File...', self)

        actions['step_prev'] = QAction(icon['step_prev'], 'Previous Step',
                                       self)
        actions['step_prev'].setShortcut(QKeySequence.MoveToPreviousChar)
        actions['step_prev'].triggered.connect(self.action_step_prev)

        actions['step_next'] = QAction(icon['step_next'], 'Next Step', self)
        actions['step_next'].setShortcut(QKeySequence.MoveToNextChar)
        actions['step_next'].triggered.connect(self.action_step_next)

        actions['page_prev'] = QAction(icon['page_prev'], 'Previous Page',
                                       self)
        actions['page_prev'].setShortcut(QKeySequence.MoveToPreviousPage)
        actions['page_prev'].triggered.connect(self.action_page_prev)

        actions['page_next'] = QAction(icon['page_next'], 'Next Page', self)
        actions['page_next'].setShortcut(QKeySequence.MoveToNextPage)
        actions['page_next'].triggered.connect(self.action_page_next)

        actions['X_more'] = QAction(icon['zoomprev'], 'Wider Time Window',
                                    self)
        actions['X_more'].setShortcut(QKeySequence.ZoomIn)
        actions['X_more'].triggered.connect(self.action_X_more)

        actions['X_less'] = QAction(icon['zoomnext'], 'Narrower Time Window',
                                    self)
        actions['X_less'].setShortcut(QKeySequence.ZoomOut)
        actions['X_less'].triggered.connect(self.action_X_less)

        actions['Y_less'] = QAction(icon['zoomin'], 'Larger Amplitude', self)
        actions['Y_less'].setShortcut(QKeySequence.MoveToPreviousLine)
        actions['Y_less'].triggered.connect(self.action_Y_less)

        actions['Y_more'] = QAction(icon['zoomout'], 'Smaller Amplitude', self)
        actions['Y_more'].setShortcut(QKeySequence.MoveToNextLine)
        actions['Y_more'].triggered.connect(self.action_Y_more)

        actions['download'] = QAction(icon['download'], 'Download Whole File',
                                      self)
        actions['download'].triggered.connect(self.action_download)

        self.action = actions  # actions was already taken

    def create_menubar(self):
        """Create the whole menubar, based on actions.

        Notes
        -----
        TODO: bookmarks are unique (might have the same text) and are not
              mutually exclusive

        TODO: events are not unique and are not mutually exclusive

        TODO: states are not unique and are mutually exclusive

        """
        actions = self.action

        menubar = self.menuBar()
        menu_file = menubar.addMenu('File')
        menu_file.addAction(actions['open_rec'])
        menu_file.addAction(actions['open_note'])
        menu_file.addSeparator()
        menu_file.addAction('Open Sleep Scoring...')
        menu_file.addAction('Save Sleep Scoring...')

        menu_time = menubar.addMenu('Time Window')
        menu_time.addAction(actions['step_prev'])
        menu_time.addAction(actions['step_next'])
        menu_time.addAction(actions['page_prev'])
        menu_time.addAction(actions['page_next'])
        menu_time.addSeparator()  # use icon cronometer
        menu_time.addAction('6 hours earlier')
        menu_time.addAction('1 hour earlier')
        menu_time.addAction('30 min earlier')
        menu_time.addAction('1 min earlier')
        menu_time.addAction('1 min later')
        menu_time.addAction('30 min later')
        menu_time.addAction('1 hour later')
        menu_time.addAction('6 hours later')

        menu_time.addSeparator()
        submenu_go = menu_time.addMenu('Go to ')
        submenu_go.addAction('Note')

        menu_view = menubar.addMenu('View')
        submenu_ampl = menu_view.addMenu('Amplitude')
        submenu_ampl.addAction(actions['Y_less'])
        submenu_ampl.addAction(actions['Y_more'])
        submenu_ampl.addSeparator()
        submenu_ampl.addAction('(presets)')
        submenu_length = menu_view.addMenu('Window Length')
        submenu_length.addAction(actions['X_more'])
        submenu_length.addAction(actions['X_less'])
        submenu_length.addSeparator()
        submenu_length.addAction('(presets)')

        menu_bookmark = menubar.addMenu('Bookmark')
        menu_bookmark.addAction('New Bookmark')
        menu_bookmark.addAction('Edit Bookmark')
        menu_bookmark.addAction('Delete Bookmark')

        menu_event = menubar.addMenu('Event')
        menu_event.addAction('New Event')
        menu_event.addAction('Edit Event')
        menu_event.addAction('Delete Event')

        menu_state = menubar.addMenu('State')
        menu_state.addAction('Add State')

        menu_window = menubar.addMenu('Windows')
        self.menu_window = menu_window

        menu_about = menubar.addMenu('About')
        menu_about.addAction('About Phypno')

    def create_toolbar(self):
        """Create the various toolbars, without keeping track of them.

        Notes
        -----
        TODO: Keep track of the toolbars, to see if they disappear.

        """
        actions = self.action

        toolbar = self.addToolBar('File Management')
        toolbar.addAction(actions['open_rec'])
        toolbar.addAction(actions['download'])

        toolbar = self.addToolBar('Scroll')
        toolbar.addAction(actions['step_prev'])
        toolbar.addAction(actions['step_next'])
        toolbar.addAction(actions['page_prev'])
        toolbar.addAction(actions['page_next'])
        toolbar.addSeparator()
        toolbar.addAction(actions['X_more'])
        toolbar.addAction(actions['X_less'])
        toolbar.addSeparator()
        toolbar.addAction(actions['Y_less'])
        toolbar.addAction(actions['Y_more'])

    def action_open(self):
        """Action: open a new dataset."""
        # filename = QFileDialog.getExistingDirectory(self, 'Open file',
        #                                            dirname(DATASET_EXAMPLE))
        self.info.update_info(DATASET_EXAMPLE)
        self.overview.update_overview()
        self.scroll.add_datetime_on_x()
        self.channels.update_channels(self.info.dataset.header['chan_name'])

    def action_step_prev(self):
        """Go to the previous step.

        Notes
        -----
        TODO: window_step_ratio should go to overview

        """
        window_start = (self.overview.window_start -
                        self.overview.window_length /
                        config.value('window_step_ratio'))
        self.overview.update_position(window_start)

    def action_step_next(self):
        """Go to the next step."""
        window_start = (self.overview.window_start +
                        self.overview.window_length /
                        config.value('window_step_ratio'))
        self.overview.update_position(window_start)

    def action_page_prev(self):
        """Go to the previous page."""
        window_start = self.overview.window_start - self.overview.window_length
        self.overview.update_position(window_start)

    def action_page_next(self):
        """Go to the next page."""
        window_start = self.overview.window_start + self.overview.window_length
        self.overview.update_position(window_start)

    def action_X_more(self):
        """Zoom in on the x-axis."""
        self.overview.window_length = self.overview.window_length * 2
        self.overview.update_position()

    def action_X_less(self):
        """Zoom out on the x-axis."""
        self.overview.window_length = self.overview.window_length / 2
        self.overview.update_position()

    def action_Y_less(self):
        """Decrease the amplitude."""
        self.scroll.set_ylimit(self.scroll.ylimit / 2)

    def action_Y_more(self):
        """Increase the amplitude."""
        self.scroll.set_ylimit(self.scroll.ylimit * 2)

    def action_download(self):
        """Start the download of the dataset."""
        self.thread_download = DownloadData(self)
        self.thread_download.one_more_interval.connect(self.overview.more_download)
        self.thread_download.start()
        self.thread_download.setPriority(QThread.Priority.LowestPriority)

    def create_widgets(self):
        """Create all the widgets and dockwidgets.

        Notes
        -----
        TODO: Probably delete previous scroll widget.

        """
        self.info = Info(self)
        self.channels = Channels(self)
        self.overview = Overview(self)
        self.stages = Stages(self)
        self.video = Video(self)
        self.scroll = Scroll(self)

        self.setCentralWidget(self.scroll)

        new_docks = [{'name': 'Information',
                      'widget': self.info,
                      'main_area': Qt.RightDockWidgetArea,
                      'extra_area': Qt.LeftDockWidgetArea,
                      },
                     {'name': 'Channels',
                      'widget': self.channels,
                      'main_area': Qt.RightDockWidgetArea,
                      'extra_area': Qt.LeftDockWidgetArea,
                      },
                      {'name': 'Stages',
                      'widget': self.states,
                      'main_area': Qt.RightDockWidgetArea,
                      'extra_area': Qt.LeftDockWidgetArea,
                      },
                     {'name': 'Video',
                      'widget': self.video,
                      'main_area': Qt.RightDockWidgetArea,
                      'extra_area': Qt.LeftDockWidgetArea,
                      },
                      {'name': 'Overview',
                      'widget': self.overview,
                      'main_area': Qt.BottomDockWidgetArea,
                      'extra_area': Qt.TopDockWidgetArea,
                      },
                      ]

        self.docks = {}
        actions = self.action
        for dock in new_docks:
            self.docks[dock['name']] = DockWidget(self,
                                                  dock['name'],
                                                  dock['widget'],
                                                  dock['main_area'] |
                                                  dock['extra_area'])
            self.addDockWidget(dock['main_area'], self.docks[dock['name']])
            new_act = QAction(icon['widget'], dock['name'], self)
            new_act.setCheckable(True)
            new_act.setChecked(True)
            new_act.triggered.connect(partial(self.toggle_menu_window,
                                              dock['name'],
                                              self.docks[dock['name']]))
            self.menu_window.addAction(new_act)
            actions[dock['name']] = new_act

            if dock['name'] in config.value('hidden_docks'):
                self.docks[dock['name']].setVisible(False)
                actions[dock['name']].setChecked(False)

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
        else:
            dockwidget.setVisible(True)
            actions[dockname].setChecked(True)


try:
    app = QApplication(argv)
except RuntimeError:
    pass

q = MainWindow()
q.show()
# q.action_open()
app.exec_()
