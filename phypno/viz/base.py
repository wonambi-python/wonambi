"""Module with helper functions for plotting

"""
from logging import getLogger
lg = getLogger('phypno')

from tempfile import mkstemp

from PyQt4.Qt import QImage, QPainter
from PyQt4.Qt import QPixmap, QBuffer, QIODevice, QByteArray


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

        This works for 2D, we need to check for 3d
        """
        scene = self._widget.scene()
        self.image = QImage(scene.sceneRect().size().toSize(), QImage.Format_RGB32)
        _painter = QPainter(self.image)
        scene.render(_painter)

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.ReadWrite)
        self.image.save(buffer, 'PNG')
        buffer.close()

        return bytes(byte_array)
