from __future__ import division
from numpy import diff, squeeze, arange
from PyQt4.QtGui import (QMainWindow, QAction, QIcon, QToolBar, QFileDialog,
                          QGraphicsView, QGraphicsScene)
from pyqtgraph import PlotWidget
from phypno import Dataset

"""
configuration parameters
TODO: use ConfigParser

"""

config = {
    'idx': 0,  # location in time
    'xscroll': 300,  # amount to scroll in time in pixels
    'ylim': (-100, 100),  # size of the datawindow
    }



IconOpen = QIcon.fromTheme('document-open')
IconPrev = QIcon.fromTheme('go-previous')
IconNext = QIcon.fromTheme('go-next')
IconUp = QIcon.fromTheme('go-up')
IconDown = QIcon.fromTheme('go-down')


class Scroll_Data(QMainWindow):

    def __init__(self):
        super().__init__()

        self.info = {}
        self.info['idx'] = config['idx']
        self.info['xscroll'] = config['xscroll']

        ActOpen = QAction(IconOpen, 'Open', self)
        ActOpen.triggered.connect(self.ActOpen)

        ActPrev = QAction(IconPrev, 'Previous Page', self)
        ActPrev.setShortcut('<')
        ActPrev.triggered.connect(self.ActPrev)

        ActNext = QAction(IconNext, 'Next Page', self)
        ActNext.setShortcut('>')
        ActNext.triggered.connect(self.ActNext)

        menu = self.addToolBar('File Management')
        menu.addAction(ActOpen)

        menu = self.addToolBar('Scroll')
        menu.addAction(ActPrev)
        menu.addAction(ActNext)



    def ActOpen(self):
        self.info['dataset'] = QFileDialog.getOpenFileName(self,
                                                              'Open file',
                    '/home/gio/tools/phypno/test/data')

        self.info['d'] = Dataset(self.info['dataset'])

        self.plot_data()

    def ActPrev(self):
        self.info['idx'] -= self.info['xscroll']
        self.plot_data()

    def ActNext(self):
        self.info['idx'] += self.info['xscroll']
        self.plot_data()

    def plot_data(self):
        begsam = self.info['idx']
        endsam = begsam + self.info['xscroll']
        data = self.info['d'].read_data(chan=['PZ'],
                                                     begsam=begsam,
                                                     endsam=endsam)
        p = PlotWidget()
        dat, time = data()
        p.plotItem.plot(time, squeeze(dat, axis=0))
        self.setCentralWidget(p)



q = Scroll_Data()
q.show()





    def ActUp(self):

        self.info['time'] += self.info['xscroll']
        self.addChannels()

    def ActDown(self):

        self.info['time'] += self.info['xscroll']
        self.addChannels()


class SleepScoring(QMainWindow):

    def __init__(self):
        super().__init__()

        self.info = info

        self.initUI()

    def initUI(self):
        """Initialize the Graphical User Interface

        This function should take care of add a toolbar, add a scene and view,
        and setting the general layout of the figure

        """

        self.scene = QGraphicsScene()
        self.addChannels()

        self.view = QGraphicsView(self.scene, self)
        self.view.setGeometry(0, 25, 700, 500)

        self.addToolBar = self.toolbar()
        self.setGeometry(400, 300, 800, 600) # TODO: nicer way to specify location
        self.setWindowTitle('Sleep Scoring')
        self.show()


    def addChannels(self):

        self.scene.clear()
        for i in arange(3):
            l = squeeze(readdat(i + 1, self.info['time']))
            ypos = self.info['chandist'] * i
            self.scene.addPath(plotLine(arange(400), l, (100, 500), (ypos,
                                        ypos + self.info['chandist']),
                                        self.info['ylim']))

ex = SleepScoring()