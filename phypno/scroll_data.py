# %%
from datetime import timedelta
from logging import getLogger, INFO
from numpy import squeeze, floor
from os.path import basename, dirname
from sys import argv, exit
from PySide.QtCore import Qt, QSettings, QThread, Signal, Slot
from PySide.QtGui import (QApplication,
                          QMainWindow,
                          QGridLayout,
                          QHBoxLayout,
                          QVBoxLayout,
                          QFormLayout,
                          QWidget,
                          QDockWidget,
                          QPushButton,
                          QLabel,
                          QLineEdit,
                          QComboBox,
                          QInputDialog,
                          QListWidget,
                          QScrollBar,
                          QProgressBar,
                          QListWidgetItem,
                          QFileDialog,
                          QGroupBox,
                          QColorDialog,
                          QAction,
                          QKeySequence,
                          QIcon,
                          QAbstractItemView,
                          QPen,
                          QColor,)
from PySide.phonon import Phonon
from pyqtgraph import PlotWidget, setConfigOption
from pyqtgraph.graphicsItems.AxisItem import AxisItem

lg = getLogger('phypno')  # replace with lg = getLogger(__name__)
lg.setLevel(INFO)

from phypno import Dataset
from phypno.trans import Montage, Filter

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
# DATASET_EXAMPLE = '/home/gio/tools/phypno/test/data/sample.edf'
# DATASET_EXAMPLE = '/home/gio/Copy/presentations_x/video/VideoFileFormat_1'

setConfigOption('background', 'w')

config = QSettings("phypno", "scroll_data")
config.setValue('window_start', 0)
config.setValue('window_length', 30)
config.setValue('ylimit', 100)
config.setValue('read_intervals', 60)  # pre-read file every X seconds


def _convert_movie_to_relative_time(begsam, endsam, movie, s_freq):
    all_movie = []
    for m in movie:
        if begsam < m['start_sample']:
            if endsam > m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': 0,
                                  'rel_end': 0})
            elif endsam > m['start_sample'] and endsam < m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': 0,
                                  'rel_end': (m['end_sample'] -
                                              endsam) / s_freq})

        elif begsam > m['start_sample']:
            if begsam < m['end_sample'] and endsam > m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': (begsam -
                                                m['start_sample']) / s_freq,
                                  'rel_end': 0})
            elif endsam < m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': (begsam -
                                                m['start_sample']) / s_freq,
                                  'rel_end': (m['end_sample'] -
                                              endsam) / s_freq})
    return all_movie


# %%
class Info(QGroupBox):    # maybe as QWidget
    """Displays information about the dataset.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    filename : str
        the full path of the file.
    dataset : instance of phypno.Dataset
        the dataset already read in.

    Methods
    -------
    read_dataset : reads dataset from filename
    display_info : displays information about the dataset

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.filename = None
        self.dataset = None

    def read_dataset(self, filename):
        self.filename = filename
        self.dataset = Dataset(filename)
        self.display_info()

    def display_info(self):
        header = self.dataset.header

        filename = QLabel('Filename: ' + basename(self.filename))
        filename.setToolTip('TODO: click here to open a new file')
        s_freq = QLabel('Sampl. Freq: ' + str(header['s_freq']))
        n_chan = QLabel('N. Channels: ' + str(len(header['chan_name'])))
        start_time = QLabel('Start Time: ' +
                            header['start_time'].strftime('%H:%M:%S'))
        start_time.setToolTip('Recording date is considered "Personally ' +
                              'identifiable information"')
        endtime = header['start_time'] + timedelta(seconds=header['n_samples']
                                                   / header['s_freq'])

        end_time = QLabel('End Time: ' + endtime.strftime('%H:%M:%S'))
        end_time.setToolTip('Recording date is considered "Personally ' +
                              'identifiable information"')

        vbox = QVBoxLayout()
        vbox.addWidget(filename)
        vbox.addWidget(s_freq)
        vbox.addWidget(n_chan)
        vbox.addWidget(start_time)
        vbox.addWidget(end_time)
        vbox.addStretch(1)
        self.setLayout(vbox)


# q = Info(None)
# q.show()
# q.read_dataset(DATASET_EXAMPLE)

# %%

class Channels(QGroupBox):  # maybe as QWidget
    """Allows user to choose channels, and filters.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    chan_name : list of str
        list of all the channels
    groups : list of dict
        groups of channels, with keys: 'name', 'chan_to_plot', 'ref_chan',
        'color', 'filter'

    Methods
    -------
    read_channels : reads the channels and updates the widget.
    display_channels : displays the whole widget
    create_list : creates list of channels (one for those to plot, one for ref)

    """

    def __init__(self, parent):
        super().__init__()
        # self.setTitle('Channels')

        self.parent = parent
        self.chan_name = None
        self.groups = [{'name': 'general',
                      'chan_to_plot': [],
                      'ref_chan': [],
                      'color': QColor('black'),
                      'filter': {'low_cut': None, 'high_cut': None},
                      },
                      ]

    def read_channels(self, chan_name):
        self.chan_name = chan_name
        self.display_channels()

    def display_channels(self):

        addButton = QPushButton('New')
        addButton.clicked.connect(lambda: self.ask_name('new'))
        renameButton = QPushButton('Rename')
        renameButton.clicked.connect(lambda: self.ask_name('rename'))
        colorButton = QPushButton('Color')
        colorButton.clicked.connect(self.color_group)
        self.colorButton = colorButton
        delButton = QPushButton('Delete')
        delButton.clicked.connect(self.delete_group)

        self.hpEdit = QLineEdit('')
        self.lpEdit = QLineEdit('')

        okButton = QPushButton('apply')
        okButton.clicked.connect(self.okButton)

        self.list_grp = QComboBox()
        for one_grp in self.groups:
            self.list_grp.addItem(one_grp['name'])

        self.list_grp.activated.connect(self.update_chan_grp)
        self.current = self.list_grp.currentText()

        hdr = QGridLayout()
        hdr.addWidget(addButton, 0, 0)
        hdr.addWidget(renameButton, 0, 1)
        hdr.addWidget(colorButton, 1, 0)
        hdr.addWidget(delButton, 1, 1)

        filt = QFormLayout()
        filt.addRow('High-Pass', self.hpEdit)
        filt.addRow('Low-Pass', self.lpEdit)

        layout = QGridLayout()
        layout.addWidget(self.list_grp, 0, 0)
        layout.addLayout(hdr, 0, 1)
        layout.addWidget(QLabel('Channels to Visualize'), 1, 0)
        layout.addWidget(QLabel('Reference Channels'), 1, 1)
        layout.addLayout(filt, 3, 0)
        layout.addWidget(okButton, 3, 1)

        self.setLayout(layout)
        self.layout = layout
        self.update_list_grp()

    def create_list(self, selected_chan):
        l = QListWidget()
        ExtendedSelection = QAbstractItemView.SelectionMode(3)
        l.setSelectionMode(ExtendedSelection)
        for chan in self.chan_name:
            item = QListWidgetItem(chan)
            l.addItem(item)
            if chan in selected_chan:
                item.setSelected(True)
            else:
                item.setSelected(False)
        return l

    def update_chan_grp(self):
        selectedItems = self.l0.selectedItems()
        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())

        selectedItems = self.l1.selectedItems()
        ref_chan = []
        for selected in selectedItems:
            ref_chan.append(selected.text())

        hp = self.hpEdit.text()
        if hp == '':
            low_cut = None
        else:
            low_cut = float(hp)

        lp = self.lpEdit.text()
        if lp == '':
            high_cut = None
        else:
            high_cut = float(lp)

        idx = [x['name'] for x in self.groups].index(self.current)
        self.groups[idx]['chan_to_plot'] = chan_to_plot
        self.groups[idx]['ref_chan'] = ref_chan
        self.groups[idx]['filter']['low_cut'] = low_cut
        self.groups[idx]['filter']['high_cut'] = high_cut

        self.update_list_grp()

    def update_list_grp(self):
        current = self.list_grp.currentText()
        idx = [x['name'] for x in self.groups].index(current)
        l0 = self.create_list(self.groups[idx]['chan_to_plot'])
        l1 = self.create_list(self.groups[idx]['ref_chan'])
        self.layout.addWidget(l0, 2, 0)
        self.layout.addWidget(l1, 2, 1)
        self.l0 = l0
        self.l1 = l1
        self.current = current  # update index

    def okButton(self):
        self.update_chan_grp()
        self.parent.overview.update_position()

    def ask_name(self, action):
        self.inputdialog = QInputDialog()
        self.inputdialog.show()
        if action == 'new':
            self.inputdialog.textValueSelected.connect(self.new_group)
        if action == 'rename':
            self.inputdialog.textValueSelected.connect(self.rename_group)

    def new_group(self):
        new_grp_name = self.inputdialog.textValue()
        self.groups.append({'name': new_grp_name,
                              'chan_to_plot': [],
                              'ref_chan': [],
                              'color': QColor('black'),
                              'filter': {'low_cut': None, 'high_cut': None},
                              })
        idx = self.list_grp.currentIndex()
        self.list_grp.insertItem(idx + 1, new_grp_name)
        self.list_grp.setCurrentIndex(idx + 1)
        self.update_list_grp()

    def rename_group(self):
        new_grp_name = self.inputdialog.textValue()
        idx = [x['name'] for x in self.groups].index(self.current)
        self.groups[idx]['name'] = new_grp_name
        self.current = new_grp_name

        idx = self.list_grp.currentIndex()
        self.list_grp.setItemText(idx, new_grp_name)

    def color_group(self):
        idx = [x['name'] for x in self.groups].index(self.current)
        newcolor = QColorDialog.getColor(self.groups[idx]['color'])
        self.groups[idx]['color'] = newcolor

    def delete_group(self):
        idx = self.list_grp.currentIndex()
        self.list_grp.removeItem(idx)
        self.groups.pop(idx)
        self.update_list_grp()


# c = Channels(None)
# c.show()
# c.read_channels(d.header['chan_name'])

# %

class Overview(QWidget):
    """Shows an overview of data, such as hypnogram and data in memory.

    Attributes
    ----------
    window_start : float
        start time of the window being plotted (in s).
    window_length : float
        length of the window being plotted (in s).

    Methods
    -------
    read_duration : reads full duration and update maximum.
    update_length : change length of the page step.
    update_position : if value changes, call scroll functions.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.window_start = config.value('window_start')
        self.window_length = config.value('window_length')

        self.scrollbar = QScrollBar()
        self.scrollbar.setOrientation(Qt.Orientation.Horizontal)
        self.scrollbar.sliderReleased.connect(self.update_position)

        self.progressbar = QProgressBar()

        layout = QVBoxLayout()
        layout.addWidget(self.scrollbar)
        layout.addWidget(self.progressbar)
        self.setLayout(layout)

        self.update_length(self.window_length)

    def read_duration(self):
        header = self.parent.info.dataset.header
        maximum = header['n_samples'] / header['s_freq']
        self.scrollbar.setMaximum(maximum - self.window_length)

    def update_length(self, new_length):
        self.window_length = new_length
        self.scrollbar.setPageStep(new_length)

    def update_position(self, new_position=None):
        if new_position is not None:
            self.window_start = new_position
            self.scrollbar.setValue(new_position)
        else:
            self.window_start = self.scrollbar.value()
        lg.info('Overview.update_position: read_data')
        self.parent.scroll.read_data()
        lg.info('Overview.update_position: plot_scroll')
        self.parent.scroll.plot_scroll()


# %%

class Video(QWidget):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.movie_info = None

        self.widget = Phonon.VideoWidget()
        self.video = Phonon.MediaObject()

        self.button = QPushButton('Start')
        self.button.clicked.connect(self.start_stop)
        Phonon.createPath(self.video, self.widget)

        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def load_video(self):
        dataset = self.parent.info.dataset
        movies = dataset.header['orig']['movies']
        s_freq = dataset.header['orig']['movie_s_freq']
        overview = self.parent.overview
        begsam = overview.window_start * s_freq
        endsam = (overview.window_start + overview.window_length) * s_freq
        lg.info('Video.load_video: begsam: ' + str(begsam) + ' endsam: ' +
                str(endsam))
        movie_info = _convert_movie_to_relative_time(begsam, endsam, movies,
                                                     s_freq)
        self.movie_info = movie_info
        self.add_sources()

        # The signal is only emitted for the last source in the media queue
        self.video.setPrefinishMark(movie_info[-1]['rel_end'] * 1e3)
        self.video.prefinishMarkReached.connect(self.stop_movie)

    def add_sources(self):
        self.video.clear()
        sources = []
        for m in self.movie_info:
            sources.append(Phonon.MediaSource(m['filename']))
        self.video.enqueue(sources)

    def start_stop(self):
        if self.button.text() == 'Start':
            self.button.setText('Stop')
            self.load_video()
            self.video.play()
            self.video.seek(self.movie_info[0]['rel_start'] * 1e3)

        elif self.button.text() == 'Stop':
            self.button.setText('Start')
            self.video.stop()

    def stop_movie(self):
        pass
        # self.video.stop()  this doesn't work, I don't know why


class Scroll(QWidget):
    """
        read_data : read data
    plot_scroll : plot data to scroll
    set_ylimit : set y limits for scroll data
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.ylimit = config.value('ylimit')
        self.data = None
        self.chan_plot = None

        layout = QGridLayout()
        layout.setVerticalSpacing(0)

        self.setLayout(layout)
        self.layout = layout

    def read_data(self):
        window_start = self.parent.overview.window_start
        window_end = window_start + self.parent.overview.window_length
        dataset = self.parent.info.dataset

        chan_to_read = []
        for one_grp in self.parent.channels.groups:
            chan_to_read.extend(one_grp['chan_to_plot'] +
                                one_grp['ref_chan'])
        data = dataset.read_data(chan=chan_to_read,
                                 begtime=window_start,
                                 endtime=window_end)
        self.data = data

    def plot_scroll(self):
        data = self.data
        layout = self.layout

        chan_plot = []
        row = 0
        for one_grp in self.parent.channels.groups:
            mont = Montage(ref_chan=one_grp['ref_chan'])
            data1 = mont(data)
            if one_grp['filter']['low_cut'] is not None:
                hpfilt = Filter(low_cut=one_grp['filter']['low_cut'],
                                s_freq=data.s_freq)
                data1 = hpfilt(data1)
            if one_grp['filter']['high_cut'] is not None:
                lpfilt = Filter(high_cut=one_grp['filter']['high_cut'],
                                s_freq=data.s_freq)
                data1 = lpfilt(data1)

            for chan in one_grp['chan_to_plot']:
                dat, time = data1(chan=[chan])
                chan_plot.append(PlotWidget())
                chan_plot[row].plotItem.plot(time, squeeze(dat, axis=0),
                                             pen=QPen(one_grp['color']))
                chan_plot[row].plotItem.setLabels(left=chan)
                chan_plot[row].plotItem.showAxis('bottom', False)
                chan_plot[row].plotItem.setXRange(time[0], time[-1])
                layout.addWidget(chan_plot[row], row, 0)
                row += 1

        chan_plot[row - 1].plotItem.showAxis('bottom', True)
        self.chan_plot = chan_plot
        self.set_ylimit()

    def set_ylimit(self, new_ylimit=None):
        if new_ylimit is not None:
            self.ylimit = new_ylimit
        chan_plot = self.chan_plot
        for single_chan_plot in chan_plot:
            single_chan_plot.plotItem.setYRange(-1 * self.ylimit,
                                                self.ylimit)

    def add_datetime_on_x(self):
        start_time = self.parent.info.dataset.header['start_time']

        def tickStrings(axis, values, c, d):
            if axis.orientation == 'bottom':
                strings = []
                for v in values:
                    strings.append((start_time +
                                    timedelta(seconds=v)).strftime('%H:%M:%S'))
            else:
                strings = [str(x) for x in values]
            return strings

        AxisItem.tickStrings = tickStrings

# %%
class DownloadData(QThread):
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
        filename = QFileDialog.getExistingDirectory(self, 'Open file',
                                                    dirname(DATASET_EXAMPLE))
        self.info.read_dataset(filename)
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


# q = MainWindow()
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


# menu:
# FILE: open recording, open notes, open sleep scoring, save sleep scoring
# NOTES: new note, edit note, delete note
# SCORES: new score, add rater
# VIEW: amplitude (presets), window length (presets)
# WINDOWS: list all the windows

if __name__ == '__main__':
    app = QApplication(argv)
    q = MainWindow()
    exit(app.exec_())
