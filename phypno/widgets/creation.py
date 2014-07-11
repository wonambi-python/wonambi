"""Functions used when creating a new window.

"""
from functools import partial
from os.path import dirname, join, realpath


from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QAction,
                         QIcon,
                         QKeySequence,
                         )

from .settings import Settings
from .channels import Channels
from .info import Info
from .overview import Overview
from .notes import Notes, Bookmarks, Events
from .traces import Traces
from .detect import Detect
from .spectrum import Spectrum
from .video import Video

from .utils import DockWidget, keep_recent_recordings

HIDDEN_DOCKS = ['Detect']

icon_path = join(dirname(realpath(__file__)), '..', '..', 'var', 'icons',
                 'oxygen')
ICON = {
    'open_rec': join(icon_path, 'document-open.png'),
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
    }


def create_actions(MAIN):
    """Create all the possible actions."""
    actions = {}
    actions['open_rec'] = QAction(QIcon(ICON['open_rec']),
                                  'Open Recording...', MAIN)
    actions['open_rec'].setShortcut(QKeySequence.Open)
    actions['open_rec'].triggered.connect(MAIN.action_open_rec)

    max_recording_history = MAIN.config.value['max_recording_history']
    recent_recs = keep_recent_recordings(max_recording_history)
    actions['recent_rec'] = []
    for one_recent_rec in recent_recs:
        action_recent = QAction(one_recent_rec, MAIN)
        action_recent.triggered.connect(partial(MAIN.action_open_rec,
                                                one_recent_rec))
        actions['recent_rec'].append(action_recent)

    actions['open_bookmarks'] = QAction('Open Bookmark File...', MAIN)
    actions['open_events'] = QAction('Open Events File...', MAIN)
    actions['open_stages'] = QAction('Open Stages File...', MAIN)
    actions['open_stages'].triggered.connect(MAIN.action_open_stages)

    actions['open_settings'] = QAction(QIcon(ICON['settings']),
                                          'Settings', MAIN)
    actions['open_settings'].triggered.connect(MAIN.open_settings)
    actions['close_wndw'] = QAction(QIcon(ICON['quit']), 'Quit', MAIN)
    actions['close_wndw'].triggered.connect(MAIN.close)

    actions['step_prev'] = QAction(QIcon(ICON['step_prev']),
                                   'Previous Step', MAIN)
    actions['step_prev'].setShortcut(QKeySequence.MoveToPreviousChar)
    actions['step_prev'].triggered.connect(MAIN.action_step_prev)

    actions['step_next'] = QAction(QIcon(ICON['step_next']),
                                   'Next Step', MAIN)
    actions['step_next'].setShortcut(QKeySequence.MoveToNextChar)
    actions['step_next'].triggered.connect(MAIN.action_step_next)

    actions['page_prev'] = QAction(QIcon(ICON['page_prev']),
                                   'Previous Page', MAIN)
    actions['page_prev'].setShortcut(QKeySequence.MoveToPreviousPage)
    actions['page_prev'].triggered.connect(MAIN.action_page_prev)

    actions['page_next'] = QAction(QIcon(ICON['page_next']),
                                   'Next Page', MAIN)
    actions['page_next'].setShortcut(QKeySequence.MoveToNextPage)
    actions['page_next'].triggered.connect(MAIN.action_page_next)

    actions['X_more'] = QAction(QIcon(ICON['zoomprev']),
                                'Wider Time Window', MAIN)
    actions['X_more'].setShortcut(QKeySequence.ZoomIn)
    actions['X_more'].triggered.connect(MAIN.action_X_more)

    actions['X_less'] = QAction(QIcon(ICON['zoomnext']),
                                'Narrower Time Window', MAIN)
    actions['X_less'].setShortcut(QKeySequence.ZoomOut)
    actions['X_less'].triggered.connect(MAIN.action_X_less)

    actions['Y_less'] = QAction(QIcon(ICON['zoomin']),
                                'Larger Amplitude', MAIN)
    actions['Y_less'].setShortcut(QKeySequence.MoveToPreviousLine)
    actions['Y_less'].triggered.connect(MAIN.action_Y_more)

    actions['Y_more'] = QAction(QIcon(ICON['zoomout']),
                                'Smaller Amplitude', MAIN)
    actions['Y_more'].setShortcut(QKeySequence.MoveToNextLine)
    actions['Y_more'].triggered.connect(MAIN.action_Y_less)

    actions['Y_wider'] = QAction(QIcon(ICON['ydist_more']),
                                 'Larger Y Distance', MAIN)
    actions['Y_wider'].triggered.connect(MAIN.action_Y_wider)

    actions['Y_tighter'] = QAction(QIcon(ICON['ydist_less']),
                                   'Smaller Y Distance', MAIN)
    actions['Y_tighter'].triggered.connect(MAIN.action_Y_tighter)

    MAIN.action = actions  # actions was already taken


def create_menubar(MAIN):
    """Create the whole menubar, based on actions."""
    actions = MAIN.action

    """ ------ FILE ------ """
    menubar = MAIN.menuBar()
    menu_file = menubar.addMenu('File')
    menu_file.addAction(actions['open_rec'])
    submenu_recent = menu_file.addMenu('Recent Recordings')
    for one_action_recent in actions['recent_rec']:
        submenu_recent.addAction(one_action_recent)

    menu_download = menu_file.addMenu('Download File')
    menu_download.setIcon(QIcon(ICON['download']))
    act = menu_download.addAction('Whole File')
    act.triggered.connect(MAIN.action_download)
    act = menu_download.addAction('30 Minutes')
    act.triggered.connect(partial(MAIN.action_download, 30 * 60))
    act = menu_download.addAction('1 Hour')
    act.triggered.connect(partial(MAIN.action_download, 60 * 60))
    act = menu_download.addAction('3 Hours')
    act.triggered.connect(partial(MAIN.action_download, 3 * 60 * 60))
    act = menu_download.addAction('6 Hours')
    act.triggered.connect(partial(MAIN.action_download, 6 * 60 * 60))

    menu_file.addSeparator()
    menu_file.addAction(actions['open_bookmarks'])
    menu_file.addAction(actions['open_events'])
    menu_file.addAction(actions['open_stages'])
    menu_file.addSeparator()
    menu_file.addAction(actions['open_settings'])
    menu_file.addSeparator()
    menu_file.addAction(actions['close_wndw'])

    """ ------ NAVIGATION ------ """
    menu_time = menubar.addMenu('Navigation')
    menu_time.addAction(actions['step_prev'])
    menu_time.addAction(actions['step_next'])
    menu_time.addAction(actions['page_prev'])
    menu_time.addAction(actions['page_next'])
    menu_time.addSeparator()  # use icon cronometer
    act = menu_time.addAction('6 Hours Earlier')
    act.setIcon(QIcon(ICON['chronometer']))
    act.triggered.connect(partial(MAIN.action_add_time, -6 * 60 * 60))
    act = menu_time.addAction('1 Hour Earlier')
    act.setIcon(QIcon(ICON['chronometer']))
    act.triggered.connect(partial(MAIN.action_add_time, -60 * 60))
    act = menu_time.addAction('10 Minutes Earlier')
    act.setIcon(QIcon(ICON['chronometer']))
    act.triggered.connect(partial(MAIN.action_add_time, -10 * 60))
    act = menu_time.addAction('10 Minutes Later')
    act.setIcon(QIcon(ICON['chronometer']))
    act.triggered.connect(partial(MAIN.action_add_time, 10 * 60))
    act = menu_time.addAction('1 Hour Later')
    act.setIcon(QIcon(ICON['chronometer']))
    act.triggered.connect(partial(MAIN.action_add_time, 60 * 60))
    act = menu_time.addAction('6 Hours Later')
    act.setIcon(QIcon(ICON['chronometer']))
    act.triggered.connect(partial(MAIN.action_add_time, 6 * 60 * 60))

    """ ------ VIEW ------ """
    menu_view = menubar.addMenu('View')
    submenu_ampl = menu_view.addMenu('Amplitude')
    submenu_ampl.addAction(actions['Y_less'])
    submenu_ampl.addAction(actions['Y_more'])
    submenu_ampl.addSeparator()
    for x in sorted(MAIN.config.value['y_scale_presets'], reverse=True):
        act = submenu_ampl.addAction('Set to ' + str(x))
        act.triggered.connect(partial(MAIN.action_Y_ampl, x))

    submenu_dist = menu_view.addMenu('Distance Between Traces')
    submenu_dist.addAction(actions['Y_wider'])
    submenu_dist.addAction(actions['Y_tighter'])
    submenu_dist.addSeparator()
    for x in sorted(MAIN.config.value['y_distance_presets'],
                    reverse=True):
        act = submenu_dist.addAction('Set to ' + str(x))
        act.triggered.connect(partial(MAIN.action_Y_dist, x))

    submenu_length = menu_view.addMenu('Window Length')
    submenu_length.addAction(actions['X_more'])
    submenu_length.addAction(actions['X_less'])
    submenu_length.addSeparator()
    for x in sorted(MAIN.config.value['window_length_presets'],
                    reverse=True):
        act = submenu_length.addAction('Set to ' + str(x))
        act.triggered.connect(partial(MAIN.action_X_length, x))

    """ ------ ANNOTATIONS ------ """
    menu_annot = menubar.addMenu('Annotations')
    menu_annot.addSeparator()

    submenu_bookmark = menu_annot.addMenu('Bookmark')
    submenu_bookmark.addAction('New Bookmark')
    submenu_bookmark.addAction('Edit Bookmark')
    submenu_bookmark.addAction('Delete Bookmark')

    submenu_event = menu_annot.addMenu('Event')
    submenu_event.addAction('New Event')
    submenu_event.addAction('Edit Event')
    submenu_event.addAction('Delete Event')

    submenu_stage = menu_annot.addMenu('Stage')
    submenu_stage.addAction('Select stage (TODO)')

    menu_window = menubar.addMenu('Windows')
    MAIN.menu_window = menu_window

    menu_about = menubar.addMenu('About')
    menu_about.addAction('About Phypno')


def create_toolbar(MAIN):
    """Create the various toolbars, without keeping track of them.

    """
    actions = MAIN.action

    toolbar = MAIN.addToolBar('File Management')
    toolbar.addAction(actions['open_rec'])

    toolbar = MAIN.addToolBar('Scroll')
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
    toolbar.addAction(actions['Y_wider'])
    toolbar.addAction(actions['Y_tighter'])


def create_widgets(MAIN):
    """Create all the widgets and dockwidgets.

    Notes
    -----
    I tried to be consistent and use lambda for connect, but somehow
    partial works well while lambda passes always the same argument.

    """
    MAIN.info = Info(MAIN)
    MAIN.channels = Channels(MAIN)
    MAIN.spectrum = Spectrum(MAIN)
    MAIN.overview = Overview(MAIN)
    MAIN.notes = Notes(MAIN)
    MAIN.bookmarks = Bookmarks(MAIN)
    MAIN.events = Events(MAIN)
    MAIN.detect = Detect(MAIN)
    MAIN.video = Video(MAIN)
    MAIN.traces = Traces(MAIN)
    MAIN.settings = Settings(MAIN)

    MAIN.setCentralWidget(MAIN.traces)

    new_docks = [{'name': 'Information',
                  'widget': MAIN.info,
                  'main_area': Qt.LeftDockWidgetArea,
                  'extra_area': Qt.RightDockWidgetArea,
                  },
                 {'name': 'Channels',
                  'widget': MAIN.channels,
                  'main_area': Qt.RightDockWidgetArea,
                  'extra_area': Qt.LeftDockWidgetArea,
                  },
                 {'name': 'Spectrum',
                  'widget': MAIN.spectrum,
                  'main_area': Qt.RightDockWidgetArea,
                  'extra_area': Qt.LeftDockWidgetArea,
                  },
                 {'name': 'Annotations',
                  'widget': MAIN.notes,
                  'main_area': Qt.LeftDockWidgetArea,
                  'extra_area': Qt.RightDockWidgetArea,
                  },
                 {'name': 'Bookmarks',
                  'widget': MAIN.bookmarks,
                  'main_area': Qt.LeftDockWidgetArea,
                  'extra_area': Qt.RightDockWidgetArea,
                  },
                 {'name': 'Events',
                  'widget': MAIN.events,
                  'main_area': Qt.LeftDockWidgetArea,
                  'extra_area': Qt.RightDockWidgetArea,
                  },
                 {'name': 'Detect',
                  'widget': MAIN.detect,
                  'main_area': Qt.LeftDockWidgetArea,
                  'extra_area': Qt.RightDockWidgetArea,
                  },
                 {'name': 'Video',
                  'widget': MAIN.video,
                  'main_area': Qt.LeftDockWidgetArea,
                  'extra_area': Qt.RightDockWidgetArea,
                  },
                 {'name': 'Overview',
                  'widget': MAIN.overview,
                  'main_area': Qt.BottomDockWidgetArea,
                  'extra_area': Qt.TopDockWidgetArea,
                  },
                 ]

    MAIN.idx_docks = {}
    actions = MAIN.action
    for dock in new_docks:
        MAIN.idx_docks[dock['name']] = DockWidget(MAIN,
                                                  dock['name'],
                                                  dock['widget'],
                                                  dock['main_area'] |
                                                  dock['extra_area'])
        MAIN.addDockWidget(dock['main_area'], MAIN.idx_docks[dock['name']])
        new_act = QAction(QIcon(ICON['widget']), dock['name'], MAIN)
        new_act.setCheckable(True)
        new_act.setChecked(True)
        new_act.triggered.connect(partial(MAIN.toggle_menu_window,
                                          dock['name'],
                                          MAIN.idx_docks[dock['name']]))
        MAIN.menu_window.addAction(new_act)
        actions[dock['name']] = new_act

        if dock['name'] in HIDDEN_DOCKS:
            MAIN.idx_docks[dock['name']].setVisible(False)
            actions[dock['name']].setChecked(False)

    MAIN.tabifyDockWidget(MAIN.idx_docks['Information'],
                          MAIN.idx_docks['Video'])
    MAIN.idx_docks['Information'].raise_()

    MAIN.tabifyDockWidget(MAIN.idx_docks['Annotations'],
                          MAIN.idx_docks['Bookmarks'])
    MAIN.tabifyDockWidget(MAIN.idx_docks['Bookmarks'],
                          MAIN.idx_docks['Events'])
    MAIN.tabifyDockWidget(MAIN.idx_docks['Events'],
                          MAIN.idx_docks['Detect'])
    MAIN.idx_docks['Annotations'].raise_()
