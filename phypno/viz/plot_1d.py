import pyqtgraph as pg


win = pg.GraphicsWindow(title="Basic plotting examples")
win.resize(1000,600)
win.setWindowTitle('pyqtgraph example: Plotting')

# Enable antialiasing for prettier plots
pg.setConfigOptions(antialias=True)

p2 = win.addPlot(title="Multiple curves")


def plot_data(data, xaxis='time', xlog=False, ylog=False):
    """Plot data in 2d.

    """


    xval = getattr(data, xaxis)
    for i_ch in range(len(data.chan_name)):
        p2.plot(xval, data.data[i_ch, :])

