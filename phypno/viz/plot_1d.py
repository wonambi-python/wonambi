from pyqtgraph import GraphicsWindow


def plot_data(data, xaxis='time', xlog=False, ylog=False):
    """Plot data in 2d.

    """
    win = GraphicsWindow(title="plot data")
    xval = getattr(data, xaxis)

    for i_ch in range(len(data.chan_name)):
        p = win.addPlot(title=data.chan_name[i_ch])
        p.plot(xval, data.data[i_ch, :])
        win.nextRow()

    return win  # avoid garbage-collection
