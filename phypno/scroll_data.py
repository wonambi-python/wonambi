# %%
from datetime import timedelta
from logging import getLogger, INFO
from numpy import squeeze
from sys import argv
from PySide.QtCore import Qt
from PySide.QtGui import (QApplication,
                          QMainWindow,
                          QGridLayout,
                          QHBoxLayout,
                          QWidget,
                          QDockWidget,
                          QPushButton,
                          QLabel,
                          QComboBox,
                          QInputDialog,
                          QListWidget,
                          QListWidgetItem,
                          QFileDialog,
                          QColorDialog,
                          QAction,
                          QKeySequence,
                          QIcon,
                          QAbstractItemView,
                          QPen,
                          QColor,)
from pyqtgraph import PlotWidget, setConfigOption

lg = getLogger('phypno')  # replace with lg = getLogger(__name__)
lg.setLevel(INFO)

from phypno import Dataset
from phypno.trans import Montage

"""
configuration parameters
TODO: use ConfigParser

"""
from pyqtgraph.graphicsItems.AxisItem import AxisItem



try:
    app = QApplication(argv)
except RuntimeError:
    pass


DATASET_EXAMPLE = ('/home/gio/recordings/MG71/eeg/raw/' +
                   'MG71_eeg_sessA_d01_21_17_40')
# DATASET_EXAMPLE = '/home/gio/tools/phypno/test/data/sample.edf'

config = {
    'win_beg': 0,
    'win_len': 30,
    'ylim': 100,
    }

setConfigOption('background', 'w')

# %%
class SelectChannels(QWidget):
    """Create a widget to choose channels.

    Parameters
    ----------
    chan_name : list of str
        list of all the possible channels
    chan_grp : list of dict
        group of channels, each containing information on the group such as
        name, chan_to_plot, ref_chan, color, filter (as dict)

    Attributes
    ----------
    chan_to_plot : list of str
        list of channels to plot

    """
    def __init__(self, chan_name, chan_grp, main_wndw):
        super().__init__()

        self.all_chan = chan_name
        self.chan_grp = chan_grp
        self.main_wndw = main_wndw

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
        self.main_wndw.chan = self.chan_grp
        self.main_wndw.create_scroll()
        self.main_wndw.read_data()
        self.main_wndw.plot_scroll()

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



# all_chan = ['c' + str(i) for i in range(10)]
# chan_grp = [{'name': 'ant', 'chan_to_plot': ['c1', 'c2'], 'ref_chan': ['c3'], 'color': QColor('black')}, {'name': 'pos', 'chan_to_plot': ['c4', 'c2'], 'ref_chan': ['c1'], 'color': None}]
# q = SelectChannels(all_chan, chan_grp, None)

# %%

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


class Scroll_Data(QMainWindow):
    """Scroll through data.

    Methods
    -------
    create_actions : add self.action
    create_toolbar : add toolbars
    create_scroll : create main widget, scroll + scroll_layout
    read_data : read data
    plot_scroll : plot data to scroll
    set_ylimit : set y limits for scroll data
    action_*** : various actions

    Attributes
    ----------
    action : dict
        names of all the actions to perform
    viz : dict
        visualization options, such as window start time, window height and
        width.
    chan : list of dict
        the dict contains information about the group of channels.
    dataset : dict
        information about the dataset, such as name, instance of Dataset.
    data : dict
        current data, time stamps.
    widgets : dict
        pointers to active widgets, to avoid garbage collection
    chan_plot : dict
        pointers to each individual channel plot

    """
    def __init__(self):
        super().__init__()

        self.viz = {
            'win_beg': config['win_beg'],  # beginning of the window
            'win_len': config['win_len'],  # end of the window
            'ylim': config['ylim'],  # max of the y axis
            }
        self.chan = [{'name': 'General',
                      'chan_to_plot': [],
                      'ref_chan': [],
                      'color': QColor('black'),
                      'filter': {},
                      }]
        self.dataset = {
            'filename': None,  # name of the file or directory
            'dataset': None,  # instance of Dataset
            }
        self.data = {
            'data': None,
            }
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

    def action_nextpage(self):
        self.viz['win_beg'] += self.viz['win_len']
        self.read_data()
        self.plot_scroll()

    def action_X_more(self):
        """It would be nice to have predefined zoom levels.
        Also, a value that can be shown and edited.
        """
        self.viz['win_len'] *= 2
        self.read_data()
        self.plot_scroll()

    def action_X_less(self):
        self.viz['win_len'] /= 2
        self.read_data()
        self.plot_scroll()

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
        sel_chan = SelectChannels(self.dataset['dataset'].header['chan_name'],
                                  self.chan,
                                  self)
        self.widgets['sel_chan'] = sel_chan

    def create_scroll(self):
        """Probably delete previous scroll widget.
        """
        scroll = QWidget()
        layout = QGridLayout()
        layout.setVerticalSpacing(0)

        scroll.setLayout(layout)
        self.setCentralWidget(scroll)

        self.widgets['scroll'] = scroll
        self.widgets['scroll_layout'] = layout

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


q = Scroll_Data()


"""
dockWidget = QDockWidget("Select Channel", self)
dockWidget.setAllowedAreas(Qt.LeftDockWidgetArea |

dockWidget.setWidget(s)
self.addDockWidget(Qt.RightDockWidgetArea, dockWidget)
                           Qt.RightDockWidgetArea)
"""
