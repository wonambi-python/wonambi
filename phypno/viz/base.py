"""Module with helper functions for plotting

"""
from logging import getLogger
lg = getLogger('phypno')

from tempfile import mkstemp

from IPython.display import Image  # TODOL extra dependency on ipython, but _repr_png is practically only used by ipython
from PyQt4.Qt import QImage, QPainter


def convert_color(dat, colormap):
    """Simple way to convert values between 0 and 1 into color.
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
        extra dependency on ipython, but _repr_png is practically only used by
        ipython. Plus it needs to write to file and read from file.

        I'll need to understand QImage and QPainter better.
        """
        scene = self._widget.scene()
        image = QImage(scene.sceneRect().size().toSize(), QImage.Format_ARGB32)
        self._painter = QPainter(image)  # otherwise it gets garbage-collected
        scene.render(self._painter)

        tmp_png = mkstemp(suffix='.png')[1]
        image.save(tmp_png)
        self._widget.close()

        ipython_image = Image(filename=tmp_png)

        return ipython_image
