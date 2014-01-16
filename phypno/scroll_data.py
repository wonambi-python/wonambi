# %%
from numpy import diff, squeeze, arange
from sys import argv
from PySide.QtCore import QCoreApplication, Qt
from PySide.QtGui import (QMainWindow, QAction, QIcon, QToolBar, QFileDialog,
                          QGraphicsView, QGraphicsScene, QApplication,
                          QGridLayout, QWidget, QStatusBar, QDockWidget)
from PySide.QtGui import (QListWidget, QListWidgetItem, QAbstractItemView,
                          QPushButton, QVBoxLayout, QHBoxLayout, QWidget)
from pyqtgraph import PlotWidget, LayoutWidget

from phypno import Dataset

"""
configuration parameters
TODO: use ConfigParser

"""

app = QApplication(argv)

config = {
    'idx': 0,  # location in time
    'xscroll': 30,  # amount to scroll in time in pixels
    'ylim': -100,  # size of the datawindow
    }

# %%


class SelectChannels(QWidget):
    """Create a widget to choose channels.

    Parameters
    ----------
    chan_name : list of str
        list of all the possible channels
    chan_to_plot : list of str
        list of channels to plot

    Attributes
    ----------
    chan_to_plot : list of str
        list of channels to plot

    """
    def __init__(self, chan_name, chan_to_plot, main_wndw):
        super().__init__()

        self.main_wndw = main_wndw

        okButton = QPushButton("OK")
        okButton.clicked.connect(self.okButton)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.cancelButton)

        l = QListWidget()
        ExtendedSelection = QAbstractItemView.SelectionMode(3)
        l.setSelectionMode(ExtendedSelection)
        for chan in chan_name:
            item = QListWidgetItem(chan)
            l.addItem(item)
            if chan in chan_to_plot:
                item.setSelected(True)
            else:
                item.setSelected(False)
        self.list = l

        hbox = QHBoxLayout()
        hbox.addWidget(cancelButton)
        hbox.addWidget(okButton)

        vbox = QVBoxLayout()
        vbox.addWidget(l)
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        self.setWindowTitle('Select Channels')
        self.show()

    def okButton(self):
        selectedItems = self.list.selectedItems()
        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())

        self.main_wndw.info['chan_to_plot'] = chan_to_plot
        self.main_wndw.plot_data()

        self.close()

    def cancelButton(self):
        self.close()


# %%

IconOpen = QIcon.fromTheme('document-open')
IconPrev = QIcon.fromTheme('go-previous')
IconNext = QIcon.fromTheme('go-next')
IconUp = QIcon.fromTheme('go-up')
IconDown = QIcon.fromTheme('go-down')
IconZoomIn = QIcon.fromTheme('zoom-in')
IconZoomOut = QIcon.fromTheme('zoom-out')
IconZoomNext = QIcon.fromTheme('zoom-next')
IconZoomPrev = QIcon.fromTheme('zoom-previous')
IconSelChan = QIcon.fromTheme('mail-mark-task')


class Scroll_Data(QMainWindow):

    def __init__(self):
        super().__init__()

        self.info = {}
        self.info['idx'] = config['idx']
        self.info['xscroll'] = config['xscroll']
        self.info['ylim'] = config['ylim']

        self.create_toolbar()
        self.setGeometry(400, 300, 800, 600)
        self.setWindowTitle('Sleep Scoring')
        self.show()

    def create_toolbar(self):
        ActOpen = QAction(IconOpen, 'Open', self)
        ActOpen.triggered.connect(self.ActOpen)

        ActPrev = QAction(IconPrev, 'Previous Page', self)
        ActPrev.setShortcut('<')
        ActPrev.triggered.connect(self.ActPrev)

        ActNext = QAction(IconNext, 'Next Page', self)
        ActNext.setShortcut('>')
        ActNext.triggered.connect(self.ActNext)

        ActXup = QAction(IconZoomPrev, 'Larger X', self)
        ActXup.setShortcut('+')
        ActXup.triggered.connect(self.ActXUp)

        ActXdown = QAction(IconZoomNext, 'Smaller X', self)
        ActXdown.setShortcut('-')
        ActXdown.triggered.connect(self.ActXDown)

        ActYup = QAction(IconZoomIn, 'Larger Y', self)
        ActYup.setShortcut('+')
        ActYup.triggered.connect(self.ActYUp)

        ActYdown = QAction(IconZoomOut, 'Smaller Y', self)
        ActYdown.setShortcut('-')
        ActYdown.triggered.connect(self.ActYDown)

        SelChan = QAction(IconSelChan, 'Select Channels', self)
        SelChan.triggered.connect(self.SelChan)

        menu = self.addToolBar('File Management')
        menu.addAction(ActOpen)

        menu = self.addToolBar('Scroll')
        menu.addAction(ActPrev)
        menu.addAction(ActNext)
        menu.addSeparator()
        menu.addAction(ActXup)
        menu.addAction(ActXdown)
        menu.addSeparator()
        menu.addAction(ActYup)
        menu.addAction(ActYdown)

        menu = self.addToolBar('Selection')
        menu.addAction(SelChan)

    def ActOpen(self):
        #self.info['dataset'] = QFileDialog.getOpenFileName(self,
        #                                                    'Open file',
        #            '/home/gio/recordings/MG71/eeg/raw')
        self.info['dataset'] = '/home/gio/recordings/MG71/eeg/raw/MG71_eeg_sessA_d01_09_53_17'
        # self.info['dataset'] = '/home/gio/tools/phypno/test/data/sample.edf'
        self.info['d'] = Dataset(self.info['dataset'])
        self.info['chan_to_plot'] = self.info['d'].header['chan_name'][1:5]
        self.plot_data()

    def ActPrev(self):
        self.info['idx'] -= self.info['xscroll']
        self.plot_data()

    def ActNext(self):
        self.info['idx'] += self.info['xscroll']
        self.plot_data()

    def ActXUp(self):
        self.info['xscroll'] *= 2
        self.plot_data()

    def ActXDown(self):
        self.info['xscroll'] /= 2
        self.plot_data()

    def ActYUp(self):
        self.info['ylim'] /= 2
        self.set_ylimit()

    def ActYDown(self):
        self.info['ylim'] *= 2
        self.set_ylimit()

    def SelChan(self):
        dockWidget = QDockWidget("Select Channel", self)
        dockWidget.setAllowedAreas(Qt.LeftDockWidgetArea |
                                   Qt.RightDockWidgetArea)
        s = SelectChannels(self.info['d'].header['chan_name'],
                           self.info['chan_to_plot'], self)
        dockWidget.setWidget(s)
        self.addDockWidget(Qt.RightDockWidgetArea, dockWidget)
        self.s = s  # garbage collection

    def plot_data(self):
        begsam = self.info['idx']
        endsam = begsam + self.info['xscroll']
        chan_to_plot = self.info['chan_to_plot']
        data = self.info['d'].read_data(chan=chan_to_plot, begtime=begsam,
                                        endtime=endsam)
        self.p = QGridLayout()
        w = QWidget()
        w.setLayout(self.p)
        self.setCentralWidget(w)

        chan_plot = []
        for row, chan in enumerate(chan_to_plot):
            dat, time = data(chan=[chan])
            chan_plot.append(PlotWidget())
            chan_plot[row].plotItem.plot(time, squeeze(dat, axis=0))
            chan_plot[row].plotItem.setXRange(time[0], time[-1])
            self.p.addWidget(chan_plot[row], row, 0)


    def set_ylimit(self):
        self.p.plotItem.setYRange(-1 * self.info['ylim'],
                                  self.info['ylim'])


q = Scroll_Data()
