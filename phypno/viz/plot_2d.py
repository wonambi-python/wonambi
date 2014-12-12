
"""Module to plot all the elements as flat images.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import max, min, meshgrid, linspace
from scipy.interpolate import griddata
from vispy.io.image import _make_png
from vispy.scene import SceneCanvas
from vispy.scene.visuals import Image

from .base import convert_color


RESOLUTION = 200


class Viz2:
    def __init__(self):
        """Class to generate lines."""
        self._canvas = SceneCanvas()

    def add_data(self, data, trial=0, limits_z=None, colormap='cool'):
        """
        Parameters
        ----------
        data : any instance of DataType
            Duck-typing should help
        trial : int
            index of the trial to plot
        limits_z : tuple, optional
            limits on the z-axis (if unspecified, it's the max across subplots)
        colormap : str
            one of the implemented colormaps.
        """
        dat = data(trial=trial)

        if limits_z is None:
            max_z = max(dat)
            min_z = min(dat)
        else:
            min_z, max_z = limits_z

        dat = (dat - min_z) / (max_z - min_z)

        _plot_image(self, dat, colormap)
        self._canvas.show()

    def add_topo(self, chan, values, limits=None, colormap='cool'):
        """
        Parameters
        ----------
        chan : instance of Channels
            channels to be plotted
        values : ndarray
            vector with the values to plot
        limits : tuple, optional
            limits on the z-axis (if unspecified, it's the max across subplots)
        colormap : str
            one of the implemented colormaps.
        """
        if limits is None:
            max_z = max(values)
            min_z = min(values)
        else:
            min_z, max_z = limits

        values = (values - min_z) / (max_z - min_z)

        xy = chan.return_xy()

        min_xy = min(xy, axis=0)
        max_xy = max(xy, axis=0)

        x_grid, y_grid = meshgrid(linspace(min_xy[0], max_xy[0], RESOLUTION),
                                  linspace(min_xy[1], max_xy[1], RESOLUTION))

        dat = griddata(xy, values, (x_grid, y_grid), method='linear')

        _plot_image(self, dat, colormap)
        self._canvas.show()

    def _repr_png_(self):
        """This is used by ipython to plot inline.

        Notes
        -----
        It uses _make_png, which is a private function. Otherwise it needs to
        write to file and read from file.
        """
        self._canvas.show()
        image = self._canvas.render()
        self._canvas.close()
        img = _make_png(image).tobytes()

        return img


def _plot_image(self, dat, colormap):
    """function that actually plots the image in vispy.

    Parameters
    ----------
    self : instance of Viz2
        we need this for _canvas
    dat : ndarray
        matrix with the data to be plotted
    colormap : str
        one of the implemented colormaps.
    """
    viewbox = self._canvas.central_widget.add_view()
    img_data = convert_color(dat, colormap)
    img = Image(img_data)
    viewbox.add(img)

    viewbox.camera.rect = (0, 0) + dat.shape[::-1]
