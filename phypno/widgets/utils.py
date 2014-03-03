from logging import getLogger
lg = getLogger(__name__)

from functools import partial

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import (QDockWidget,
                          QIcon,
                          QMessageBox,
                          QPainterPath,
                          )

config = QSettings("phypno", "scroll_data")
MAX_RECORDING_HISTORY = 20

icon = {
    'open_rec': QIcon.fromTheme('document-open'),
    'page_prev': QIcon.fromTheme('go-previous-view'),
    'page_next': QIcon.fromTheme('go-next-view'),
    'step_prev': QIcon.fromTheme('go-previous'),
    'step_next': QIcon.fromTheme('go-next'),
    'chronometer': QIcon.fromTheme('chronometer'),
    'up': QIcon.fromTheme('go-up'),
    'down': QIcon.fromTheme('go-down'),
    'zoomin': QIcon.fromTheme('zoom-in'),
    'zoomout': QIcon.fromTheme('zoom-out'),
    'zoomnext': QIcon.fromTheme('zoom-next'),
    'zoomprev': QIcon.fromTheme('zoom-previous'),
    'ydist_more': QIcon.fromTheme('format-line-spacing-triple'),
    'ydist_less': QIcon.fromTheme('format-line-spacing-normal'),
    'selchan': QIcon.fromTheme('mail-mark-task'),
    'download': QIcon.fromTheme('download'),
    'widget': QIcon.fromTheme('window-duplicate'),
    'preferences': QIcon.fromTheme('configure'),
    'quit': QIcon.fromTheme('window-close'),
    }


def create_menubar(mainwindow):
    """Create the whole menubar, based on actions.

    Notes
    -----
    TODO: bookmarks are unique (might have the same text) and are not
          mutually exclusive

    TODO: events are not unique and are not mutually exclusive

    TODO: states are not unique and are mutually exclusive

    """
    preferences = mainwindow.preferences.values
    actions = mainwindow.action

    menubar = mainwindow.menuBar()
    menu_file = menubar.addMenu('File')
    menu_file.addAction(actions['open_rec'])
    submenu_recent = menu_file.addMenu('Recent Recordings')
    for one_action_recent in actions['recent_rec']:
        submenu_recent.addAction(one_action_recent)

    menu_download = menu_file.addMenu('Download File')
    menu_download.setIcon(icon['download'])
    act = menu_download.addAction('Whole File')
    act.triggered.connect(mainwindow.action_download)
    act = menu_download.addAction('30 Minutes')
    act.triggered.connect(partial(mainwindow.action_download, 30 * 60))
    act = menu_download.addAction('1 Hour')
    act.triggered.connect(partial(mainwindow.action_download, 60 * 60))
    act = menu_download.addAction('3 Hours')
    act.triggered.connect(partial(mainwindow.action_download, 3 * 60 * 60))
    act = menu_download.addAction('6 Hours')
    act.triggered.connect(partial(mainwindow.action_download, 6 * 60 * 60))

    menu_file.addSeparator()
    menu_file.addAction(actions['open_bookmarks'])
    menu_file.addAction(actions['open_events'])
    menu_file.addAction(actions['open_stages'])
    menu_file.addSeparator()
    menu_file.addAction(actions['open_preferences'])
    menu_file.addSeparator()
    menu_file.addAction(actions['close_wndw'])

    menu_time = menubar.addMenu('Time Window')
    menu_time.addAction(actions['step_prev'])
    menu_time.addAction(actions['step_next'])
    menu_time.addAction(actions['page_prev'])
    menu_time.addAction(actions['page_next'])
    menu_time.addSeparator()  # use icon cronometer
    act = menu_time.addAction('6 Hours Earlier')
    act.setIcon(icon['chronometer'])
    act.triggered.connect(partial(mainwindow.action_add_time, -6 * 60 * 60))
    act = menu_time.addAction('1 Hour Earlier')
    act.setIcon(icon['chronometer'])
    act.triggered.connect(partial(mainwindow.action_add_time, -60 * 60))
    act = menu_time.addAction('10 Minutes Earlier')
    act.setIcon(icon['chronometer'])
    act.triggered.connect(partial(mainwindow.action_add_time, -10 * 60))
    act = menu_time.addAction('10 Minutes Later')
    act.setIcon(icon['chronometer'])
    act.triggered.connect(partial(mainwindow.action_add_time, 10 * 60))
    act = menu_time.addAction('1 Hour Later')
    act.setIcon(icon['chronometer'])
    act.triggered.connect(partial(mainwindow.action_add_time, 60 * 60))
    act = menu_time.addAction('6 Hours Later')
    act.setIcon(icon['chronometer'])
    act.triggered.connect(partial(mainwindow.action_add_time, 6 * 60 * 60))

    menu_time.addSeparator()
    submenu_go = menu_time.addMenu('Go to ')
    submenu_go.addAction('Note')

    menu_view = menubar.addMenu('View')
    submenu_ampl = menu_view.addMenu('Amplitude')
    submenu_ampl.addAction(actions['Y_less'])
    submenu_ampl.addAction(actions['Y_more'])
    submenu_ampl.addSeparator()
    for x in sorted(preferences['traces/y_scale_presets'], reverse=True):
        act = submenu_ampl.addAction('Set to ' + str(x))
        act.triggered.connect(partial(mainwindow.action_Y_ampl, x))

    submenu_dist = menu_view.addMenu('Distance Between Traces')
    submenu_dist.addAction(actions['Y_wider'])
    submenu_dist.addAction(actions['Y_tighter'])
    submenu_dist.addSeparator()
    for x in sorted(preferences['traces/y_distance_presets'], reverse=True):
        act = submenu_dist.addAction('Set to ' + str(x))
        act.triggered.connect(partial(mainwindow.action_Y_dist, x))

    submenu_length = menu_view.addMenu('Window Length')
    submenu_length.addAction(actions['X_more'])
    submenu_length.addAction(actions['X_less'])
    submenu_length.addSeparator()
    for x in sorted(preferences['overview/window_length_presets'],
                    reverse=True):
        act = submenu_length.addAction('Set to ' + str(x))
        act.triggered.connect(partial(mainwindow.action_X_length, x))

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
    mainwindow.menu_window = menu_window

    menu_about = menubar.addMenu('About')
    menu_about.addAction('About Phypno')


def create_toolbar(mainwindow):
    """Create the various toolbars, without keeping track of them.

    Notes
    -----
    TODO: Keep track of the toolbars, to see if they disappear.

    """
    actions = mainwindow.action

    toolbar = mainwindow.addToolBar('File Management')
    toolbar.addAction(actions['open_rec'])

    toolbar = mainwindow.addToolBar('Scroll')
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


class DockWidget(QDockWidget):
    """Simple DockWidget, that, when closes, changes the check on the menu.

    """
    def __init__(self, parent, name, subwidget, area):
        super().__init__(name, parent)
        self.parent = parent
        self.name = name
        self.setAllowedAreas(area)
        self.setWidget(subwidget)

    def closeEvent(self, event):
        """Override the function, so that it closes and changes the check in
        the menu.

        Parameters
        ----------
        event : unknown
            we don't care.

        """
        self.parent.toggle_menu_window(self.name, self)


class Path(QPainterPath):

    def __init__(self, x, y):
        super().__init__()

        self.moveTo(x[0], y[0])
        for i_x, i_y in zip(x, y):
            self.lineTo(i_x, i_y)


def keep_recent_recordings(new_recording=None):
    """Keep track of the most recent recordings.

    Parameters
    ----------
    new_recording : str, optional
        path to file

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
        if len(history) > MAX_RECORDING_HISTORY:
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
