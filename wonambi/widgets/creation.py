"""Functions used when creating a new window.

"""
from logging import getLogger
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction,
                             QDockWidget,
                             QMessageBox,
                             )

from .settings import (Settings, SlowWaveHelp, SpindleHelp,
                       EvtAnalysisHelp)  # has to be first
from .utils import ICON   # has to be second
from .labels import Labels
from .channels import Channels
from .info import Info, ExportDatasetDialog
from .overview import Overview
from .notes import Notes, MergeDialog
from .detect_dialogs import SpindleDialog, SWDialog
from .modal_widgets import EventAnalysisDialog
from .analysis import AnalysisDialog, PlotDialog
from .spectrum import Spectrum
from .traces import Traces
from .video import Video


lg = getLogger(__name__)


def create_widgets(MAIN):
    """Create all the widgets and dockwidgets. It also creates actions to
    toggle views of dockwidgets in dockwidgets.
    """

    """ ------ CREATE WIDGETS ------ """
    MAIN.labels = Labels(MAIN)
    MAIN.channels = Channels(MAIN)
    MAIN.notes = Notes(MAIN)
    MAIN.merge_dialog = MergeDialog(MAIN)
    MAIN.export_dataset_dialog = ExportDatasetDialog(MAIN)
    MAIN.spindle_dialog = SpindleDialog(MAIN)
    MAIN.slow_wave_dialog = SWDialog(MAIN)
    MAIN.spindle_help = SpindleHelp(MAIN)
    MAIN.slowwave_help = SlowWaveHelp(MAIN)
    MAIN.event_analysis_dialog = EventAnalysisDialog(MAIN)
    MAIN.evt_analysis_help = EvtAnalysisHelp(MAIN)
    MAIN.analysis_dialog = AnalysisDialog(MAIN)
    MAIN.plot_dialog = PlotDialog(MAIN)
    MAIN.overview = Overview(MAIN)
    MAIN.spectrum = Spectrum(MAIN)
    MAIN.traces = Traces(MAIN)
    MAIN.video = Video(MAIN)
    MAIN.settings = Settings(MAIN)  # depends on all widgets apart from Info
    MAIN.info = Info(MAIN)  # this has to be the last, it depends on settings

    MAIN.setCentralWidget(MAIN.traces)

    """ ------ LIST DOCKWIDGETS ------ """
    new_docks = [{'name': 'Information',
                  'widget': MAIN.info,
                  'main_area': Qt.LeftDockWidgetArea,
                  'extra_area': Qt.RightDockWidgetArea,
                  },
                 {'name': 'Labels',
                  'widget': MAIN.labels,
                  'main_area': Qt.RightDockWidgetArea,
                  'extra_area': Qt.LeftDockWidgetArea,
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
    MAIN.tabifyDockWidget(idx_docks['Channels'],
                          idx_docks['Labels'])
    idx_docks['Information'].raise_()


def create_actions(MAIN):
    """Create all the possible actions."""
    actions = MAIN.action  # actions was already taken

    """ ------ OPEN SETTINGS ------ """
    actions['open_settings'] = QAction(QIcon(ICON['settings']), 'Settings',
                                       MAIN)
    actions['open_settings'].triggered.connect(MAIN.show_settings)

    """ ------ CLOSE WINDOW ------ """
    actions['close_wndw'] = QAction(QIcon(ICON['quit']), 'Quit', MAIN)
    actions['close_wndw'].triggered.connect(MAIN.close)

    """ ------ ABOUT ------ """
    actions['about'] = QAction('About WONAMBI', MAIN)
    actions['about'].triggered.connect(MAIN.about)

    actions['aboutqt'] = QAction('About Qt', MAIN)
    actions['aboutqt'].triggered.connect(lambda: QMessageBox.aboutQt(MAIN))


def create_menubar(MAIN):
    """Create the whole menubar, based on actions."""
    actions = MAIN.action
    menubar = MAIN.menuBar()
    menubar.clear()

    """ ------ FILE ------ """
    menu_file = menubar.addMenu('File')
    menu_file.addAction(MAIN.info.action['open_dataset'])
    submenu_recent = menu_file.addMenu('Recent Datasets')
    submenu_recent.addActions(MAIN.info.action['open_recent'])
    menu_file.addAction(MAIN.info.action['export'])

    menu_file.addSeparator()
    menu_file.addAction(actions['open_settings'])
    menu_file.addSeparator()
    menu_file.addAction(actions['close_wndw'])

    """ ------ CHANNELS ------ """
    actions = MAIN.channels.action
    menu_time = menubar.addMenu('Channels')
    menu_time.addAction(actions['load_channels'])
    menu_time.addAction(actions['save_channels'])

    """ ------ NAVIGATION ------ """
    actions = MAIN.traces.action

    menu_time = menubar.addMenu('Navigation')
    menu_time.addAction(actions['step_prev'])
    menu_time.addAction(actions['step_next'])
    menu_time.addAction(actions['page_prev'])
    menu_time.addAction(actions['page_next'])
    menu_time.addSeparator()
    menu_time.addAction(actions['addtime_-6h'])
    menu_time.addAction(actions['addtime_-1h'])
    menu_time.addAction(actions['addtime_-10min'])
    menu_time.addAction(actions['addtime_10min'])
    menu_time.addAction(actions['addtime_1h'])
    menu_time.addAction(actions['addtime_6h'])
    menu_time.addSeparator()
    menu_time.addAction(actions['go_to_epoch'])
    menu_time.addAction(actions['line_up_with_epoch'])

    """ ------ VIEW ------ """
    actions = MAIN.traces.action

    menu_view = menubar.addMenu('View')
    submenu_ampl = menu_view.addMenu('Global Scaling')
    submenu_ampl.addAction(actions['Y_less'])
    submenu_ampl.addAction(actions['Y_more'])
    submenu_ampl.addSeparator()
    for x in sorted(MAIN.value('y_scale_presets'), reverse=True):
        act = submenu_ampl.addAction('Set to ' + str(x))
        act.triggered.connect(partial(MAIN.traces.Y_ampl, x))

    submenu_dist = menu_view.addMenu('Distance Between Traces')
    submenu_dist.addAction(actions['Y_wider'])
    submenu_dist.addAction(actions['Y_tighter'])
    submenu_dist.addSeparator()
    for x in sorted(MAIN.value('y_distance_presets'),
                    reverse=True):
        act = submenu_dist.addAction('Set to ' + str(x))
        act.triggered.connect(partial(MAIN.traces.Y_dist, x))

    submenu_length = menu_view.addMenu('Window Length')
    submenu_length.addAction(actions['X_more'])
    submenu_length.addAction(actions['X_less'])
    submenu_length.addSeparator()
    for x in sorted(MAIN.value('window_length_presets'),
                    reverse=True):
        act = submenu_length.addAction('Set to ' + str(x))
        act.triggered.connect(partial(MAIN.traces.X_length, x))

    menu_view.addAction(actions['cross_chan_mrk'])

    menu_view.addSeparator()
    menu_view.addAction(actions['export_svg'])

    """ ------ ANNOTATIONS ------ """
    actions = MAIN.notes.action

    menu_annot = menubar.addMenu('Annotations')
    menu_annot.addAction(actions['new_annot'])
    menu_annot.addAction(actions['load_annot'])
    menu_annot.addAction(actions['clear_annot'])
    menu_annot.addSeparator()

    submenu_rater = menu_annot.addMenu('Rater')
    submenu_rater.addAction(actions['new_rater'])
    submenu_rater.addAction(actions['del_rater'])
    submenu_rater.addSeparator()
    if MAIN.notes.annot is not None:
        for rater in sorted(MAIN.notes.annot.raters):
            act = submenu_rater.addAction(rater)
            act.triggered.connect(partial(MAIN.notes.select_rater, rater))
    menu_annot.addSeparator()

    submenu_marker = menu_annot.addMenu('Bookmark')
    submenu_marker.addAction(actions['new_bookmark'])

    submenu_event = menu_annot.addMenu('Event')
    submenu_event.addAction(actions['new_eventtype'])
    submenu_event.addAction(actions['del_eventtype'])
    submenu_event.addAction(actions['merge_events'])

    # these are the real QActions attached to notes
    submenu_stage = menu_annot.addMenu('Stage')
    submenu_stage.addActions(MAIN.notes.actions())

    submenu_mrkr = menu_annot.addMenu('Cycle')
    submenu_mrkr.addAction(actions['cyc_start'])
    submenu_mrkr.addAction(actions['cyc_end'])
    submenu_mrkr.addAction(actions['remove_cyc'])
    submenu_mrkr.addAction(actions['clear_cyc'])
    menu_annot.addSeparator()

    submenu_import = menu_annot.addMenu('Import staging')
    submenu_import.addAction(actions['import_alice'])
    submenu_import.addAction(actions['import_compumedics'])
    submenu_import.addAction(actions['import_domino'])
    submenu_import.addAction(actions['import_remlogic'])
    submenu_import.addAction(actions['import_sandman'])
    submenu_import.addAction(actions['import_fasst'])

    menu_annot.addAction(actions['export'])

    """ ------ ANALYSIS ------ """
    actions = MAIN.notes.action

    menu_analysis = menubar.addMenu('Analysis')

    submenu_detect = menu_analysis.addMenu('Detection')
    submenu_detect.addAction(actions['spindle'])
    submenu_detect.addAction(actions['slow_wave'])

    menu_analysis.addAction(actions['analyze_events'])
    menu_analysis.addAction(actions['analyze'])
    menu_analysis.addAction(actions['export_sleepstats'])


    """ ------ WINDOWS ------ """
    actions = MAIN.action

    menu_window = menubar.addMenu('Windows')
    for dockwidget_act in actions['dockwidgets']:
        menu_window.addAction(dockwidget_act)
    MAIN.menu_window = menu_window

    menu_about = menubar.addMenu('About')
    menu_about.addAction(actions['about'])
    menu_about.addAction(actions['aboutqt'])

def create_toolbar(MAIN):
    """Create the various toolbars."""
    actions = MAIN.action

    toolbar = MAIN.addToolBar('File Management')
    toolbar.setObjectName('File Management')  # for savestate
    toolbar.addAction(MAIN.info.action['open_dataset'])
    toolbar.addSeparator()
    toolbar.addAction(MAIN.channels.action['load_channels'])
    toolbar.addAction(MAIN.channels.action['save_channels'])
    toolbar.addSeparator()
    toolbar.addAction(MAIN.notes.action['new_annot'])
    toolbar.addAction(MAIN.notes.action['load_annot'])

    """ ------ SCROLL ------ """
    actions = MAIN.traces.action

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

    """ ------ ANNOTATIONS ------ """
    actions = MAIN.notes.action

    toolbar = MAIN.addToolBar('Annotations')
    toolbar.setObjectName('Annotations')

    toolbar.addAction(actions['new_bookmark'])
    toolbar.addSeparator()
    toolbar.addAction(actions['new_event'])
    toolbar.addWidget(MAIN.notes.idx_eventtype)
    toolbar.addSeparator()
    toolbar.addWidget(MAIN.notes.idx_stage)
    toolbar.addWidget(MAIN.notes.idx_quality)
