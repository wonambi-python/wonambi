"""Module to plot all the elements as flat images.

"""
from numpy import max, min, meshgrid, linspace
from scipy.interpolate import griddata
from pyqtgraph import GraphicsLayoutWidget, ImageItem, setConfigOption

from .base import Viz, Colormap

RESOLUTION = 200


class Viz2(Viz):
    def __init__(self, color='wk'):
        """Class to generate images."""
        self._color = color
        setConfigOption('foreground', self._color[0])
        setConfigOption('background', self._color[1])

        self._widget = GraphicsLayoutWidget()
        self._plots = []

    def add_data(self, data, trial=0, limits_c=None, colormap='coolwarm'):
        """
        Parameters
        ----------
        data : any instance of DataType
            Duck-typing should help
        trial : int
            index of the trial to plot
        limits_c : tuple, optional
            limits on the z-axis (if unspecified, it's the max across subplots)
        colormap : str
            one of the implemented colormaps.
        """
        dat = data(trial=trial)

        if limits_c is None:
            max_c = max(dat)
            min_c = min(dat)
        else:
            min_c, max_c = limits_c

        dat = (dat - min_c) / (max_c - min_c)
        dat = dat.T  # time on x-axis, channels on y-axis

        cmap = Colormap(colormap)
        for i in range(1):
            p = self._widget.addPlot()
            img = ImageItem(cmap.map(dat))
            p.addItem(img)
            self._plots.append(p)

        self._widget.show()

    def add_topo(self, chan, values, limits_c=None, colormap='coolwarm'):
        """
        Parameters
        ----------
        chan : instance of Channels
            channels to be plotted
        values : ndarray
            vector with the values to plot
        limits_c : tuple, optional
            limits on the z-axis (if unspecified, it's the max across subplots)
        colormap : str
            one of the implemented colormaps.
        """
        if limits_c is None:
            max_c = max(values)
            min_c = min(values)
        else:
            min_c, max_c = limits_c

        values = (values - min_c) / (max_c - min_c)

        xy = chan.return_xy()

        min_xy = min(xy, axis=0)
        max_xy = max(xy, axis=0)

        x_grid, y_grid = meshgrid(linspace(min_xy[0], max_xy[0], RESOLUTION),
                                  linspace(min_xy[1], max_xy[1], RESOLUTION))

        dat = griddata(xy, values, (x_grid, y_grid), method='linear')

        # _plot_image(self, dat, colormap)
        self._widget.show()
