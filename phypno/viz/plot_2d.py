from numpy import log, isinf, NaN
from pyqtgraph import ImageView


def plot_data(data, zlog=False):
    """Plot data in 2d.

    """
    imv = ImageView()
    imv.show()
    if zlog:
        plot_data = log(data.data[0, :, :])
        plot_data[isinf(plot_data)] = NaN
    else:
        plot_data = data.data[0, :, :]

    imv.setImage(plot_data)
    return imv  # avoid garbage-collection
