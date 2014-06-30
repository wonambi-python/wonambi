from numpy import log, min, max, meshgrid, linspace, NaN, isinf
from scipy.interpolate import griddata
from visvis import imshow, CM_JET

RESOLUTION = 200


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


def plot_topo(chan, values, v_lim=None):
    xy = chan.return_xy()

    min_xy = min(xy, axis=0)
    max_xy = max(xy, axis=0)

    x_grid, y_grid = meshgrid(linspace(min_xy[0], max_xy[0], RESOLUTION),
                              linspace(min_xy[1], max_xy[1], RESOLUTION))

    zi = griddata(xy, values, (x_grid, y_grid), method='linear')

    if v_lim is None:
        vlim = (0, max(values))
    else:
        vlim = v_lim

    img = imshow(zi, clim=vlim, cm=CM_JET)

    return img
