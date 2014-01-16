# %%
from numpy import diff, squeeze, arange
from sys import argv
from PyQt4.QtGui import (QMainWindow, QAction, QIcon, QToolBar, QFileDialog,
                          QGraphicsView, QGraphicsScene, QApplication,
                          QGridLayout, QWidget)
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

IconOpen = QIcon.fromTheme('document-open')
IconPrev = QIcon.fromTheme('go-previous')
IconNext = QIcon.fromTheme('go-next')
IconUp = QIcon.fromTheme('go-up')
IconDown = QIcon.fromTheme('go-down')
IconZoomIn = QIcon.fromTheme('zoom-in')
IconZoomOut = QIcon.fromTheme('zoom-out')
IconZoomNext = QIcon.fromTheme('zoom-next')
IconZoomPrev = QIcon.fromTheme('zoom-previous')


class Scroll_Data(QMainWindow):

    def __init__(self):
        super().__init__()

        self.info = {}
        self.info['idx'] = config['idx']
        self.info['xscroll'] = config['xscroll']
        self.info['ylim'] = config['ylim']

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

        self.setGeometry(400, 300, 800, 600)
        self.setWindowTitle('Sleep Scoring')
        self.show()

    def ActOpen(self):
        #self.info['dataset'] = QFileDialog.getOpenFileName(self,
        #                                                     'Open file',
        #            '/home/gio/tools/phypno/test/data')

        self.info['dataset'] = '/home/gio/tools/phypno/test/data/sample.edf'
        self.info['d'] = Dataset(self.info['dataset'])
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

    def plot_data(self):
        begsam = self.info['idx']
        endsam = begsam + self.info['xscroll']
        all_chan = ['PZ', 'P3']
        data = self.info['d'].read_data(chan=all_chan, begtime=begsam,
                                        endtime=endsam)
        self.p = QGridLayout()
        w = QWidget()
        w.setLayout(self.p)
        self.setCentralWidget(w)

        chan_plot = []
        for row, chan in enumerate(all_chan):
            dat, time = data(chan=[chan])
            chan_plot.append(PlotWidget())
            chan_plot[row].plotItem.plot(time, squeeze(dat, axis=0))
            chan_plot[row].plotItem.setXRange(time[0], time[-1])
            self.p.addWidget(chan_plot[row], row, 0)


    def set_ylimit(self):
        self.p.plotItem.setYRange(-1 * self.info['ylim'],
                                  self.info['ylim'])


q = Scroll_Data()

