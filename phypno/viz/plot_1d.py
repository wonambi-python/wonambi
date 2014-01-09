from pyqtgraph import GraphicsWindow, LinearRegionItem


def plot_data(data, xaxis='time', xlog=False, ylog=False):
    """Plot recordings.

    """
    win = GraphicsWindow(title="plot data")
    xval = getattr(data, xaxis)
    p1 = win.addLayout(row=1, col=0)
    p2 = win.addPlot(row=2, col=0)

    region = LinearRegionItem()
    region.setZValue(10)
    p2.addItem(region, ignoreBounds=True)

    # p1.setAutoVisible(y=True)

    for ch in data.chan_name:
        p1_sub = p1.addPlot(name=ch)
        p1_sub.plot(xval, data(chan=[ch])[0][0])
        p1_sub.hideAxis('bottom')
        p1_sub.setXLink(data.chan_name[0])
        p1_sub.setYLink(data.chan_name[0])
        p1.nextRow()

    for ch in data.chan_name:
        p2.plot(xval, data(chan=[ch])[0][0])


    def update():
        region.setZValue(10)
        minX, maxX = region.getRegion()
        p1_sub.setXRange(minX, maxX, padding=0)

    region.sigRegionChanged.connect(update)

    def updateRegion(window, viewRange):
        rgn = viewRange[0]
        region.setRegion(rgn)

    p1_sub.sigRangeChanged.connect(updateRegion)

    region.setRegion([0, 30])





    return win  # avoid garbage-collection



# methods:
#   width()
#


# toolTip() vs setToolTip('str')
# p.setXLink(data.chan_name[0])