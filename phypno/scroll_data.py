# %%
from datetime import timedelta
from logging import getLogger, INFO
from numpy import squeeze
from os.path import basename
from sys import argv
from PySide.QtCore import Qt
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

config = {
    'win_beg': 0,
    'win_len': 30,
    'ylim': 100,
    }

setConfigOption('background', 'w')

# %%
class Info(QGroupBox):
    """Display information about the dataset.

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
    read_dataset : read dataset from filename
    display_info : display information about the dataset

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.filename = None
        self.dataset = None
        self.setTitle('Information')

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

i = Info(None)
i.show()
i.read_dataset(DATASET_EXAMPLE)


# %%

class Channels(QWidget):
    """Create a widget to choose channels.

    chan_plot : dict
        pointers to each individual channel plot

    self.chan = [{'name': 'General',
                      'chan_to_plot': [],
                      'ref_chan': [],
                      'color': QColor('black'),
                      'filter': {},
                      }]

    """
    def __init__(self, parent, chan_name, chan_grp):
        super().__init__()

        self.all_chan = chan_name
        self.chan_grp = chan_grp
        self.parent = parent

        addButton = QPushButton('New')
        addButton.clicked.connect(lambda: self.ask_name('new'))
        renameButton = QPushButton('Rename')
        renameButton.clicked.connect(lambda: self.ask_name('rename'))
        colorButton = QPushButton('Color')
        colorButton.clicked.connect(self.color_group)
        self.colorButton = colorButton
        delButton = QPushButton('Delete')
        delButton.clicked.connect(self.delete_group)

        okButton = QPushButton('OK')
        okButton.clicked.connect(self.okButton)
        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(self.cancelButton)

        self.list_grp = QComboBox()
        for one_grp in chan_grp:
            self.list_grp.addItem(one_grp['name'])

        self.list_grp.activated.connect(self.update_chan_grp)
        self.current = self.list_grp.currentText()

        hdr = QHBoxLayout()
        hdr.addWidget(addButton)
        hdr.addWidget(renameButton)
        hdr.addWidget(colorButton)
        hdr.addWidget(delButton)

        hbox = QHBoxLayout()
        hbox.addWidget(cancelButton)
        hbox.addWidget(okButton)

        layout = QGridLayout()
        layout.addWidget(self.list_grp, 0, 0)
        layout.addLayout(hdr, 0, 1)
        layout.addWidget(QLabel('Channels to Visualize'), 1, 0)
        layout.addWidget(QLabel('Reference Channels'), 1, 1)
        layout.addLayout(hbox, 3, 1)

        self.layout = layout
        self.update_list_grp()

        self.setLayout(layout)
        self.setGeometry(100, 100, 480, 480)
        self.setWindowTitle('Select Channels')
        self.show()

    def create_list(self, all_chan, selected_chan):
        l = QListWidget()
        ExtendedSelection = QAbstractItemView.SelectionMode(3)
        l.setSelectionMode(ExtendedSelection)
        for chan in all_chan:
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

        idx = [x['name'] for x in self.chan_grp].index(self.current)
        self.chan_grp[idx]['chan_to_plot'] = chan_to_plot
        self.chan_grp[idx]['ref_chan'] = ref_chan

        self.update_list_grp()

    def update_list_grp(self):
        current = self.list_grp.currentText()
        idx = [x['name'] for x in self.chan_grp].index(current)
        l0 = self.create_list(self.all_chan,
                              self.chan_grp[idx]['chan_to_plot'])
        l1 = self.create_list(self.all_chan,
                              self.chan_grp[idx]['ref_chan'])
        self.layout.addWidget(l0, 2, 0)
        self.layout.addWidget(l1, 2, 1)
        self.l0 = l0
        self.l1 = l1
        self.current = current  # update index

    def okButton(self):
        self.update_chan_grp()
        self.parent.chan = self.chan_grp
        self.parent.create_scroll()
        self.parent.read_data()
        self.parent.plot_scroll()

        self.close()

    def cancelButton(self):
        self.close()

    def ask_name(self, action):
        self.inputdialog = QInputDialog()
        self.inputdialog.show()
        if action == 'new':
            self.inputdialog.textValueSelected.connect(self.new_group)
        if action == 'rename':
            self.inputdialog.textValueSelected.connect(self.rename_group)

    def new_group(self):
        new_grp_name = self.inputdialog.textValue()
        self.chan_grp.append({'name': new_grp_name,
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
        idx = [x['name'] for x in self.chan_grp].index(self.current)
        self.chan_grp[idx]['name'] = new_grp_name
        self.current = new_grp_name

        idx = self.list_grp.currentIndex()
        self.list_grp.setItemText(idx, new_grp_name)

    def color_group(self):
        idx = [x['name'] for x in self.chan_grp].index(self.current)
        newcolor = QColorDialog.getColor(self.chan_grp[idx]['color'])
        self.chan_grp[idx]['color'] = newcolor

    def delete_group(self):
        idx = self.list_grp.currentIndex()
        self.list_grp.removeItem(idx)
        self.chan_grp.pop(idx)
        self.update_list_grp()


class Overview(QScrollBar):
    """
        viz : dict
        visualization options, such as window start time, window height and
        width.

                self.viz = {
            'win_beg': config['win_beg'],  # beginning of the window
            'win_len': config['win_len'],  # end of the window
            'ylim': config['ylim'],  # max of the y axis
            }

    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setPageStep(self.parent.viz['win_len'])
        self.setMaximum(self.calculate_duration() - self.parent.viz['win_len'])
        self.setOrientation(Qt.Orientation.Horizontal)
        self.sliderReleased.connect(self.update_scroll)

    def calculate_duration(self):
        header = self.parent.dataset['dataset'].header
        return header['n_samples'] / header['s_freq']

    def update_scroll(self):
        self.parent.viz['win_beg'] = self.value()
        self.parent.read_data()
        self.parent.plot_scroll()


class Scroll(QWidget):
    """
        read_data : read data
    plot_scroll : plot data to scroll
    set_ylimit : set y limits for scroll data
    """
    def read_data(self):
        win_beg = self.viz['win_beg']
        win_end = win_beg + self.viz['win_len']

        chan_to_read = []
        for one_grp in self.chan:
            chan_to_read.extend(one_grp['chan_to_plot'] +
                                one_grp['ref_chan'])
        data = self.dataset['dataset'].read_data(chan=chan_to_read,
                                                 begtime=win_beg,
                                                 endtime=win_end)
        self.data['data'] = data

    def plot_scroll(self):
        data = self.data['data']
        layout = self.widgets['scroll_layout']

        chan_plot = []
        row = 0
        for one_grp in self.chan:
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
        self.widgets['scroll_chan'] = chan_plot
        self.set_ylimit()

    def set_ylimit(self):
        chan_plot = self.widgets['scroll_chan']
        for single_chan_plot in chan_plot:
            single_chan_plot.plotItem.setYRange(-1 * self.viz['ylim'],
                                                self.viz['ylim'])

    def add_datetime_on_x(self):
        start_time = self.dataset['dataset'].header['start_time']

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
        self.widgets = {
            'scroll': None,
            'scroll_layout': None,
            'scroll_chan': None,
            }

        self.create_actions()
        self.create_toolbar()

        self.setGeometry(400, 300, 800, 600)
        self.setWindowTitle('Sleep Scoring')
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

        actions['sel_chan'] = QAction(icon['selchan'], 'Select Channels', self)
        actions['sel_chan'].triggered.connect(self.action_select_chan)

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

        toolbar = self.addToolBar('Selection')
        toolbar.addAction(actions['sel_chan'])

    def action_open(self):
        #self.info['dataset'] = QFileDialog.getOpenFileName(self,
        #                                                    'Open file',
        #            '/home/gio/recordings/MG71/eeg/raw')
        self.dataset['filename'] = DATASET_EXAMPLE
        self.dataset['dataset'] = Dataset(self.dataset['filename'])
        self.add_datetime_on_x()
        self.action_select_chan()

    def action_prevpage(self):
        self.viz['win_beg'] -= self.viz['win_len']
        self.read_data()
        self.plot_scroll()
        self.widgets['overview'].setValue(self.viz['win_beg'])

    def action_nextpage(self):
        self.viz['win_beg'] += self.viz['win_len']
        self.read_data()
        self.plot_scroll()
        self.widgets['overview'].setValue(self.viz['win_beg'])

    def action_X_more(self):
        """It would be nice to have predefined zoom levels.
        Also, a value that can be shown and edited.
        """
        self.viz['win_len'] *= 2
        self.read_data()
        self.plot_scroll()
        self.widgets['overview'].setPageStep(self.viz['win_len'])

    def action_X_less(self):
        self.viz['win_len'] /= 2
        self.read_data()
        self.plot_scroll()
        self.widgets['overview'].setPageStep(self.viz['win_len'])

    def action_Y_less(self):
        """See comments to action_X_more.
        """
        self.viz['ylim'] /= 2
        self.set_ylimit()

    def action_Y_more(self):
        self.viz['ylim'] *= 2
        self.set_ylimit()

    def action_select_chan(self):
        """Create new widget to select channels.

        """
        sel_chan = Channels(self, self.dataset['dataset'].header['chan_name'],
                            self.chan)
        self.widgets['sel_chan'] = sel_chan

    def create_widgets(self):
        """Probably delete previous scroll widget.
        """
        scroll = QWidget()
        layout = QGridLayout()
        layout.setVerticalSpacing(0)

        scroll.setLayout(layout)
        self.setCentralWidget(scroll)

        dockWidget = QDockWidget("Overview", self)
        dockWidget.setAllowedAreas(Qt.BottomDockWidgetArea |
                                   Qt.TopDockWidgetArea)

        overview = Overview(self)
        dockWidget.setWidget(overview)
        self.addDockWidget(Qt.BottomDockWidgetArea, dockWidget)

        self.widgets['scroll'] = scroll
        self.widgets['scroll_layout'] = layout
        self.widgets['overview'] = overview


q = MainWindow()

