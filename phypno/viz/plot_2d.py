from pyqtgraph import ImageView


def plot_data(data):
    """Plot data in 2d.

    """
    imv = ImageView()
    imv.show()
    imv.setImage(data.data[0, :, :])

    return imv  # avoid garbage-collection
