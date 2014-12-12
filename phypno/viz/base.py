"""Module with helper functions for plotting

"""
from logging import getLogger
lg = getLogger('phypno')

from vispy.color.colormap import get_colormap
from vispy.io.image import _make_png


def convert_color(dat, colormap):
    """Simple way to convert a values between 0 and 1 into color.
    This function won't be necessary when vispy implements colormaps.
    """
    cmap = get_colormap(colormap)
    img_data = cmap[dat.flatten()].rgba
    return img_data.reshape(dat.shape + (4, ))


class Viz():

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
