"""Functions used when creating a new window.

"""
from logging import getLogger
lg = getLogger(__name__)

from functools import partial
from os.path import dirname, join, realpath

from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QAction,
                         QActionGroup,
                         QDockWidget,
                         QIcon,
                         QKeySequence,
                         )

from .settings import Settings
from .utils import keep_recent_recordings
from .channels import Channels
from .info import Info
from .overview import Overview
from .notes import Notes
from .traces import Traces
from .detect import Detect
from .spectrum import Spectrum
from .video import Video

HIDDEN_DOCKS = ['Detect']

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
        }


def create_widgets(MAIN):
    """Create all the widgets and dockwidgets.

    Notes
    -----
    It creates actions to toggle views of dockwidgets in dockwidgets

    """
    """ ------ CREATE WIDGETS ------ """
    MAIN.info = Info(MAIN)
    MAIN.channels = Channels(MAIN)
    MAIN.spectrum = Spectrum(MAIN)
    MAIN.overview = Overview(MAIN)
    MAIN.notes = Notes(MAIN)
    MAIN.detect = Detect(MAIN)
    MAIN.video = Video(MAIN)
    MAIN.traces = Traces(MAIN)
    MAIN.settings = Settings(MAIN)

    MAIN.setCentralWidget(MAIN.traces)

    """ ------ LIST DOCKWIDGETS ------ """
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

    """ ------ CREATE DOCKWIDGETS ------ """
    idx_docks = {}
    actions = MAIN.action

    actions['dockwidgets'] = []
    for dock in new_docks:
        dockwidget = QDockWidget(dock['name'], MAIN)
        dockwidget.setWidget(dock['widget'])
        dockwidget.setAllowedAreas(dock['main_area'] | dock['extra_area'])
        dockwidget.setObjectName(dock['name'])  # savestate

        idx_docks[dock['name']] = dockwidget
        MAIN.addDockWidget(dock['main_area'], dockwidget)

        dockwidget_action = dockwidget.toggleViewAction()
        dockwidget_action.setIcon(QIcon(ICON['widget']))

        actions['dockwidgets'].append(dockwidget_action)

    """ ------ ORGANIZE DOCKWIDGETS ------ """
    MAIN.tabifyDockWidget(idx_docks['Information'],
                          idx_docks['Video'])
    idx_docks['Information'].raise_()

    MAIN.tabifyDockWidget(idx_docks['Annotations'],
                          idx_docks['Detect'])
    idx_docks['Annotations'].raise_()


def create_actions(MAIN):
    """Create all the possible actions."""
    actions = MAIN.action  # actions was already taken
    """ ------ FILE OPERATIONS ------ """
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

    """ ------ OPEN SETTINGS ------ """
    actions['open_settings'] = QAction(QIcon(ICON['settings']),
                                       'Settings', MAIN)
    actions['open_settings'].triggered.connect(MAIN.action_show_settings)

    """ ------ CLOSE WINDOW ------ """
    actions['close_wndw'] = QAction(QIcon(ICON['quit']), 'Quit', MAIN)
    actions['close_wndw'].triggered.connect(MAIN.close)

    """ ------ VIEW ------ """
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

    """ ------ ANNOTATIONS ------ """
    actions['new_annot'] = QAction('New Annotation File...', MAIN)
    actions['new_annot'].triggered.connect(MAIN.action_new_annot)
    actions['load_annot'] = QAction('Load Annotation File...', MAIN)
    actions['load_annot'].triggered.connect(MAIN.action_load_annot)

    actions['new_rater'] = QAction('New...', MAIN)
    actions['new_rater'].triggered.connect(MAIN.action_select_rater)
    actions['del_rater'] = QAction('Delete...', MAIN)
    actions['del_rater'].triggered.connect(MAIN.action_delete_rater)

    actions['new_marker'] = QAction(QIcon(ICON['marker']), 'New Marker', MAIN)
    actions['new_marker'].setCheckable(True)
    actions['new_event'] = QAction(QIcon(ICON['event']), 'New Event Type',
                                   MAIN)
    actions['new_event'].setCheckable(True)

    uncheck_new_event = lambda: actions['new_event'].setChecked(False)
    uncheck_new_marker = lambda: actions['new_marker'].setChecked(False)
    actions['new_event'].triggered.connect(uncheck_new_marker)
    actions['new_marker'].triggered.connect(uncheck_new_event)


def create_menubar(MAIN):
    """Create the whole menubar, based on actions."""
    actions = MAIN.action
    menubar = MAIN.menuBar()
    menubar.clear()

    """ ------ FILE ------ """
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
    menu_annot.addAction(actions['new_annot'])
    menu_annot.addAction(actions['load_annot'])
    menu_annot.addSeparator()

    submenu_rater = menu_annot.addMenu('Rater')
    submenu_rater.addAction(actions['new_rater'])
    submenu_rater.addAction(actions['del_rater'])
    submenu_rater.addSeparator()
    if MAIN.notes.annot is not None:
        for rater in sorted(MAIN.notes.annot.raters):
            lg.debug('Adding rater: ' + rater)
            act = submenu_rater.addAction(rater)
            act.triggered.connect(partial(MAIN.action_select_rater, rater))
    menu_annot.addSeparator()

    submenu_marker = menu_annot.addMenu('Marker')
    submenu_marker.addAction(actions['new_marker'])
    submenu_marker.addAction('Delete Marker(TODO)')

    submenu_event = menu_annot.addMenu('Event')
    submenu_event.addAction(actions['new_event'])
    submenu_event.addAction('Delete Event (TODO)')

    submenu_stage = menu_annot.addMenu('Stage')
    submenu_stage.addActions(MAIN.notes.actions())

    menu_window = menubar.addMenu('Windows')
    for dockwidget_act in actions['dockwidgets']:
        menu_window.addAction(dockwidget_act)
    MAIN.menu_window = menu_window

    menu_about = menubar.addMenu('About')
    menu_about.addAction('About Phypno')


def create_toolbar(MAIN):
    """Create the various toolbars, without keeping track of them.

    """
    actions = MAIN.action

    toolbar = MAIN.addToolBar('File Management')
    toolbar.setObjectName('File Management')  # for savestate
    toolbar.addAction(actions['open_rec'])

    toolbar = MAIN.addToolBar('Scroll')
    toolbar.setObjectName('Scroll')  # for savestate
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

    toolbar = MAIN.addToolBar('Annotations')
    toolbar.setObjectName('Annotations')

    toolbar.addAction(actions['new_marker'])
    toolbar.addSeparator()
    toolbar.addAction(actions['new_event'])
    toolbar.addWidget(MAIN.notes.idx_eventtype)
    toolbar.addSeparator()
    toolbar.addWidget(MAIN.notes.idx_stage)
