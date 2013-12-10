from __future__ import division
from numpy import diff, squeeze
from scipy import arange
from PySide.QtGui import (QMainWindow, QAction, QIcon, QPainterPath,
                          QGraphicsView, QGraphicsScene)
from ioeeg import edf

"""
configuration parameters
TODO: use ConfigParser

"""

info = {
    'time': 0, # location in time
    'xscroll': 300, # amount to scroll in time in pixels
    'ylim': (-100, 100), # size of the datawindow
    'chandist': 150 # distance between channels
}


def plotLine(x, y, xpos, ypos, ylim=(-100, 100)):
    """Plot a line as simple as possible.

    Parameters
    ----------
    x : numpy array
        position on the x axis
    y : numpy array
        position on the x axis (actual data values)
    xpos : tuple
        min and max x-positions on the graph
    ypos : tuple
        min and max y-positions on the graph
    ylim : tuple, optional
        min and max y-values for the plot

    TODO: xpos and ypos should probably be replaced by view
    TODO: this should probably be in an independent module

    Returns
    -------
    instance of QPainterPath

    """

    path = QPainterPath()

    left = xpos[0]
    top = ypos[1]
    width = xpos[1] - xpos[0]
    height = ypos[1] - ypos[0]
    path.addRect(left, top, width, height)

    x += left
    y *= -1 # because QT counts from top, voltage is from bottom
    yratio = height / diff(ylim) # stretch factor
    y *= yratio
    y = y + top + ylim[1] * yratio

    path.moveTo(xpos[0], top + height / 2)
    for i_x, i_y in zip(x, y):
        path.lineTo(i_x, i_y)

    return path

def readdat(chan, i):
    e = edf('/home/gio/recordings/MG67/eeg/raw/MG67_d9_FEM.edf')
    d = e.readdat(chan, i, i + 400)
    return d


class SleepScoring(QMainWindow):

    def __init__(self):
        super(SleepScoring, self).__init__()
        
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

    def toolbar(self):

        # Icons
        IconOpen = QIcon.fromTheme('document-open')
        IconPrev = QIcon.fromTheme('go-previous')
        IconNext = QIcon.fromTheme('go-next')
        IconUp = QIcon.fromTheme('go-up')
        IconDown = QIcon.fromTheme('go-down')

        ActOpen = QAction(IconOpen, 'Open', self)
        ActOpen.setShortcut('CTRL+o')
        ActOpen.triggered.connect(self.close)

        ActPrev = QAction(IconPrev, 'Previous Page', self)
        ActPrev.setShortcut('<')
        ActPrev.triggered.connect(self.ActPrev)

        ActNext = QAction(IconNext, 'Next Page', self)
        ActNext.setShortcut('>')
        ActNext.triggered.connect(self.ActNext)

        toolbar = self.addToolBar('File')
        toolbar.addAction(ActOpen)

        toolbar = self.addToolBar('Scroll')
        toolbar.addAction(ActPrev)
        toolbar.addAction(ActNext)

        return toolbar

    def ActPrev(self):

        self.info['time'] -= self.info['xscroll']
        self.addChannels()
        
    def ActNext(self):

        self.info['time'] += self.info['xscroll']
        self.addChannels()

    def ActUp(self):

        self.info['time'] += self.info['xscroll']
        self.addChannels()

    def ActDown(self):

        self.info['time'] += self.info['xscroll']
        self.addChannels()

    def addChannels(self):

        self.scene.clear()
        for i in arange(3):
            l = squeeze(readdat(i + 1, self.info['time']))
            ypos = self.info['chandist'] * i
            self.scene.addPath(plotLine(arange(400), l, (100, 500), (ypos,
                                        ypos + self.info['chandist']), 
                                        self.info['ylim']))

ex = SleepScoring()