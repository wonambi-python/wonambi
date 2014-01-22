# %%
from datetime import timedelta
from logging import getLogger, INFO
from numpy import squeeze
from os.path import basename
from sys import argv
from PySide.QtCore import Qt, QSettings
from PySide.QtGui import (QApplication,
                          QMainWindow,
                          QGridLayout,
                          QHBoxLayout,
                          QVBoxLayout,
                          QWidget,
                          QDockWidget,
                          QPushButton,
                          QLabel,
                          QComboBox,
                          QInputDialog,
                          QListWidget,
                          QScrollBar,
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
from pyqtgraph import PlotWidget, setConfigOption
from pyqtgraph.graphicsItems.AxisItem import AxisItem

lg = getLogger('phypno')  # replace with lg = getLogger(__name__)
lg.setLevel(INFO)

from phypno import Dataset
from phypno.trans import Montage

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
    }

try:
    app = QApplication(argv)
except RuntimeError:
    pass


DATASET_EXAMPLE = ('/home/gio/recordings/MG71/eeg/raw/' +
                   'MG71_eeg_sessA_d01_21_17_40')
DATASET_EXAMPLE = '/home/gio/tools/phypno/test/data/sample.edf'


setConfigOption('background', 'w')

config = QSettings("phypno", "scroll_data")
config.setValue('window_start', 0)
config.setValue('window_length', 30)
config.setValue('ylimit', 100)


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
                      'filter': {},
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

        okButton = QPushButton('apply')
        okButton.clicked.connect(self.okButton)

        self.list_grp = QComboBox()
        for one_grp in self.groups:
            self.list_grp.addItem(one_grp['name'])

        self.list_grp.activated.connect(self.update_chan_grp)
        self.current = self.list_grp.currentText()

        hdr = QHBoxLayout()
        hdr.addWidget(addButton)
        hdr.addWidget(renameButton)
        hdr.addWidget(colorButton)
        hdr.addWidget(delButton)

        hbox = QHBoxLayout()
        hbox.addWidget(okButton)

        layout = QGridLayout()
        layout.addWidget(self.list_grp, 0, 0)
        layout.addLayout(hdr, 0, 1)
        layout.addWidget(QLabel('Channels to Visualize'), 1, 0)
        layout.addWidget(QLabel('Reference Channels'), 1, 1)
        layout.addLayout(hbox, 3, 1)
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

        idx = [x['name'] for x in self.groups].index(self.current)
        self.groups[idx]['chan_to_plot'] = chan_to_plot
        self.groups[idx]['ref_chan'] = ref_chan

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
                              'filter': None,
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

class Overview(QScrollBar):
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

        self.setOrientation(Qt.Orientation.Horizontal)
        self.sliderReleased.connect(self.update_position)

        self.update_length(self.window_length)

    def read_duration(self):
        header = self.parent.info.dataset.header
        maximum = header['n_samples'] / header['s_freq']
        self.setMaximum(maximum - self.window_length)

    def update_length(self, new_length):
        self.window_length = new_length
        self.setPageStep(new_length)

    def update_position(self, new_position=None):
        if new_position is not None:
            self.window_start = new_position
            self.setValue(new_position)
        else:
            self.window_start = self.value()
        self.parent.scroll.read_data()
        self.parent.scroll.plot_scroll()


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
            reref = mont(data)
            for chan in one_grp['chan_to_plot']:
                dat, time = reref(chan=[chan])
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

    def set_ylimit(self, new_ylimit):
        self.ylimit = new_ylimit
        chan_plot = self.chan_plot
        for single_chan_plot in chan_plot:
            single_chan_plot.plotItem.setYRange(-1 * new_ylimit,
                                                new_ylimit)

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

        self.action = actions  # actions was already taken

    def create_toolbar(self):
        actions = self.action

        toolbar = self.addToolBar('File Management')
        toolbar.addAction(actions['open'])

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
        #self.info['dataset'] = QFileDialog.getOpenFileName(self,
        #                                                    'Open file',
        #            '/home/gio/recordings/MG71/eeg/raw')
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

    def create_widgets(self):
        """Probably delete previous scroll widget.
        """

        info = Info(self)
        channels = Channels(self)
        overview = Overview(self)
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

        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.BottomDockWidgetArea, dockOverview)
        self.addDockWidget(Qt.RightDockWidgetArea, dockInfo)
        self.addDockWidget(Qt.RightDockWidgetArea, dockChannels)

        self.info = info
        self.channels = channels
        self.overview = overview
        self.scroll = scroll


q = MainWindow()
q.action_open()








# %%

k = Ktlx(dataset)



sampleStamp, sampleTime = _read_snc(join(k.filename, k._basename + '.snc'))
vtc = _read_vtc(join(k.filename, k._basename + '.vtc'))


begsam = 200000
endsam = begsam + 500 * 5

# TODO: find closest sampleStamp and use the one after
s_freq = (sampleStamp[-1] - sampleStamp[0]) / (sampleTime[-1] - sampleTime[0]).total_seconds()


t1 = sampleTime[0] + timedelta(seconds=(begsam - sampleStamp[0]) / s_freq)
t2 = sampleTime[0] + timedelta(seconds=(endsam - sampleStamp[0]) / s_freq)


for v in vtc:
    if t1 > v['StartTime'] and t < v['EndTime']:
        break

video_name = join(k.filename, v['MpgFileName'])
start_video = (t1 - v['StartTime']).total_seconds()
end_video = (v['EndTime'] - t2).total_seconds()


from PySide.phonon import Phonon



media_src = Phonon.MediaSource(video_name)
media_obj = Phonon.MediaObject()



def close_video():
    print('hi')
    media_obj.stop()


media_obj.setCurrentSource(media_src)

video_widget = Phonon.VideoWidget()

Phonon.createPath(media_obj, video_widget)

media_obj.setPrefinishMark(end_video * 1e3)
media_obj.prefinishMarkReached.connect(close_video)

video_widget.show()

media_obj.play()
media_obj.seek(start_video * 1e3)