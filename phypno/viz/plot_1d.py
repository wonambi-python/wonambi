from pyqtgraph import GraphicsWindow, LinearRegionItem

FIGURE_SIZE = (1280, 720)
BOTTOM_ROW = 144
WINDOW_SIZE = 30


def scroll_recordings(data, xaxis='time', xlog=False, ylog=False):
    """Plot recordings, so that you can scroll through it.

    Parameters
    ----------
    data : any instance of DataType
        Duck-typing should help
    xaxis : str, optional
        value to plot on x-axis: 'time' or 'freq'
    xlog : bool
        not implemented
    ylog : bool
        not implemented

    Returns
    -------
    win : instance of GraphicsWindow
        useful against garbage collection

    Notes
    -----
    Not really fast, it can plot up to 10 channels in a nice way.

    Much room for optimization, especially because it plots the data twice.

    """
    xval = getattr(data, xaxis)

    win = GraphicsWindow(title="Scroll Recordings", size=FIGURE_SIZE)
    p1 = win.addLayout(row=0, col=0)
    p2 = win.addPlot(row=1, col=0)
    win.ci.layout.setRowFixedHeight(1, BOTTOM_ROW)

    region = LinearRegionItem()
    region.setZValue(10)
    p2.addItem(region, ignoreBounds=True)

    p1_sub = {}
    for ch in data.chan_name:
        p1_sub[ch] = p1.addPlot(name=ch)
        p1_sub[ch].plot(xval, data(chan=[ch])[0][0])
        p1_sub[ch].hideAxis('bottom')
        p1_sub[ch].setXLink(data.chan_name[0])
        p1_sub[ch].setYLink(data.chan_name[0])
        p1.nextRow()
    p1_sub[ch].showAxis('bottom')  # only for the last one

    for ch in data.chan_name:
        p2.plot(xval, data(chan=[ch])[0][0])

    def update():
        region.setZValue(10)  # on top
        minX, maxX = region.getRegion()
        for ch in p1_sub:
            p1_sub[ch].setXRange(minX, maxX, padding=0)

    def updateRegion(window, viewRange):
        rgn = viewRange[0]
        region.setRegion(rgn)

    region.sigRegionChanged.connect(update)
    for ch in p1_sub:
        p1_sub[ch].sigRangeChanged.connect(updateRegion)

    region.setRegion([0, WINDOW_SIZE])

    return win
