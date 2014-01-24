from logging import getLogger, INFO
lg = getLogger(__name__)
lg.setLevel(INFO)

from numpy import floor
from os.path import dirname
from sys import argv, exit
from PySide.QtCore import Qt, QSettings, QThread, Signal, Slot
from PySide.QtGui import (QAction,
                          QApplication,
                          QDockWidget,
                          QFileDialog,
                          QIcon,
                          QKeySequence,
                          QMainWindow,
                          )
from pyqtgraph import setConfigOption
# change phypno.widgets into .widgets
from phypno.widgets import Info, Channels, Overview, Scroll, Video


icon = {
    'open': QIcon.fromTheme('document-open'),
    'prev': QIcon.fromTheme('go-previous'),
    'next': QIcon.fromTheme('go-next'),
    'up': QIcon.fromTheme('go-up'),
    'down': QIcon.fromTheme('go-down'),
    'zoomin': QIcon.fromTheme('zoom-in'),
    'zoomout': QIcon.fromTheme('zoom-out'),
    'zoomnext': QIcon.fromTheme('zoom-next'),
    'zoomprev': QIcon.fromTheme('zoom-previous'),
    'selchan': QIcon.fromTheme('mail-mark-task'),
    'download': QIcon.fromTheme('download'),
    }

DATASET_EXAMPLE = ('/home/gio/recordings/MG71/eeg/raw/' +
                   'MG71_eeg_sessA_d01_21_17_40')
DATASET_EXAMPLE = '/home/gio/tools/phypno/test/data/sample.edf'
# DATASET_EXAMPLE = '/home/gio/Copy/presentations_x/video/VideoFileFormat_1'

setConfigOption('background', 'w')

config = QSettings("phypno", "scroll_data")
config.setValue('window_start', 0)
config.setValue('window_length', 30)
config.setValue('ylimit', 100)
config.setValue('read_intervals', 60)  # pre-read file every X seconds


class DownloadData(QThread):
    # remember to close it
    one_more_interval = Signal(int)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        dataset = self.parent.info.dataset
        progressbar = self.parent.overview.progressbar
        total_dur = dataset.header['n_samples'] / dataset.header['s_freq']
        maximum = int(floor(total_dur / config.value('read_intervals')))
        progressbar.setMaximum(maximum - 1)

        self.maximum = maximum

    def run(self):
        dataset = self.parent.info.dataset
        one_chan = dataset.header['chan_name'][0]
        for i in range(0, self.maximum):
            dataset.read_data(chan=[one_chan],
                              begtime=i * config.value('read_intervals'),
                              endtime=i * config.value('read_intervals') + 1)
            self.one_more_interval.emit(i)

        self.exec_()

# %%

class MainWindow(QMainWindow):
    """

    Methods
    -------
    create_actions : add self.action
    create_toolbar : add toolbars
    create_widgets : create main widgets
    action_*** : various actions

    Attributes
    ----------
    action : dict
        names of all the actions to perform
    chan : list of dict
        the dict contains information about the group of channels.
    dataset : dict
        information about the dataset, such as name, instance of Dataset.
    data : dict
        current data, time stamps.
    widgets : dict
        pointers to active widgets, to avoid garbage collection

    """
    def __init__(self):
        super().__init__()

        self.info = None
        self.channels = None
        self.overview = None
        self.scroll = None

        self.thread_download = None

        self.create_actions()
        self.create_menubar()
        self.create_toolbar()
        self.create_widgets()

        self.setGeometry(400, 300, 800, 600)
        self.setWindowTitle('Scroll Data')
        self.show()

    def create_actions(self):
        actions = {}
        actions['open'] = QAction(icon['open'], 'Open', self)
        actions['open'].setShortcut(QKeySequence.Open)
        actions['open'].triggered.connect(self.action_open)

        actions['prev'] = QAction(icon['prev'], 'Previous Page', self)
        actions['prev'].setShortcut(QKeySequence.MoveToPreviousChar)
        actions['prev'].triggered.connect(self.action_prevpage)

        actions['next'] = QAction(icon['next'], 'Next Page', self)
        actions['next'].setShortcut(QKeySequence.MoveToNextChar)
        actions['next'].triggered.connect(self.action_nextpage)

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
        actions['Y_more'].setShortcut(QKeySequence.MoveToPreviousLine)
        actions['Y_more'].triggered.connect(self.action_Y_more)

        actions['download'] = QAction(icon['download'], 'Download Whole File',
                                      self)
        actions['download'].triggered.connect(self.action_download)

        self.action = actions  # actions was already taken

    def create_menubar(self):
        actions = self.action

        menubar = self.menuBar()
        menu_file = menubar.addMenu('File')
        menu_file.addAction(actions['open'])
        # menu:
        # FILE: open recording, open notes, open sleep scoring, save sleep scoring
        # NOTES: new note, edit note, delete note
        # SCORES: new score, add rater
        # VIEW: amplitude (presets), window length (presets)
        # WINDOWS: list all the windows

    def create_toolbar(self):
        actions = self.action

        toolbar = self.addToolBar('File Management')
        toolbar.addAction(actions['open'])
        toolbar.addAction(actions['download'])

        toolbar = self.addToolBar('Scroll')
        toolbar.addAction(actions['prev'])
        toolbar.addAction(actions['next'])
        toolbar.addSeparator()
        toolbar.addAction(actions['X_more'])
        toolbar.addAction(actions['X_less'])
        toolbar.addSeparator()
        toolbar.addAction(actions['Y_less'])
        toolbar.addAction(actions['Y_more'])

    def action_open(self):
        # filename = QFileDialog.getExistingDirectory(self, 'Open file',
        #                                            dirname(DATASET_EXAMPLE))
        self.info.read_dataset(DATASET_EXAMPLE)
        self.overview.read_duration()
        self.scroll.add_datetime_on_x()
        self.channels.read_channels(self.info.dataset.header['chan_name'])

    def action_prevpage(self):
        window_start = self.overview.window_start - self.overview.window_length
        self.overview.update_position(window_start)

    def action_nextpage(self):
        window_start = self.overview.window_start + self.overview.window_length
        self.overview.update_position(window_start)

    def action_X_more(self):
        """It would be nice to have predefined zoom levels.
        Also, a value that can be shown and edited.
        """
        self.overview.update_length(self.overview.window_length * 2)

    def action_X_less(self):
        self.overview.update_length(self.overview.window_length / 2)

    def action_Y_less(self):
        """See comments to action_X_more.
        """
        self.scroll.set_ylimit(self.scroll.ylimit / 2)

    def action_Y_more(self):
        self.scroll.set_ylimit(self.scroll.ylimit * 2)

    def action_download(self):
        self.thread_download = DownloadData(self)
        self.thread_download.one_more_interval.connect(self.update_progressbar)
        self.thread_download.start()
        self.thread_download.setPriority(QThread.Priority.LowestPriority)

    @Slot(int)
    def update_progressbar(self, new_value):
        self.overview.progressbar.setValue(new_value)

    def create_widgets(self):
        """Probably delete previous scroll widget.
        """

        info = Info(self)
        channels = Channels(self)
        overview = Overview(self)
        video = Video(self)
        scroll = Scroll(self)

        dockOverview = QDockWidget("Overview", self)
        dockOverview.setAllowedAreas(Qt.BottomDockWidgetArea |
                                     Qt.TopDockWidgetArea)
        dockOverview.setWidget(overview)

        dockInfo = QDockWidget("Information", self)
        dockInfo.setAllowedAreas(Qt.RightDockWidgetArea |
                                 Qt.LeftDockWidgetArea)
        dockInfo.setWidget(info)

        dockChannels = QDockWidget("Channels", self)
        dockChannels.setAllowedAreas(Qt.RightDockWidgetArea |
                                     Qt.LeftDockWidgetArea)
        dockChannels.setWidget(channels)

        dockVideo = QDockWidget("Video", self)
        dockVideo.setAllowedAreas(Qt.RightDockWidgetArea |
                                  Qt.LeftDockWidgetArea)
        dockVideo.setWidget(video)

        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.BottomDockWidgetArea, dockOverview)
        self.addDockWidget(Qt.RightDockWidgetArea, dockInfo)
        self.addDockWidget(Qt.RightDockWidgetArea, dockChannels)
        self.addDockWidget(Qt.RightDockWidgetArea, dockVideo)

        self.info = info
        self.channels = channels
        self.video = video
        self.overview = overview
        self.scroll = scroll


q = MainWindow()
# q.action_open()



# %%
"""

from PySide.QtCore import Qt
from PySide.QtGui import QGraphicsView, QGraphicsScene, QGraphicsLineItem


l = QGraphicsLineItem(0, 0, 100, 100)

scene = QGraphicsScene(0, 0, 24 * 60, 100)
scene.addItem(l)

view = QGraphicsView(scene)
# view.setSceneRect(0, 0, 200, 200)
view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
view.show()

"""


if __name__ == '__main__':
    app = QApplication(argv)
    q = MainWindow()
    exit(app.exec_())
