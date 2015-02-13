"""Module with helper functions for plotting

"""
from numpy import array, ubyte
from PyQt4.Qt import QImage, QPainter, QBuffer, QIODevice, QByteArray
from PyQt4.QtGui import QApplication
from pyqtgraph import ColorMap


class Colormap(ColorMap):

    def __init__(self, name='default'):
        if name == 'default':
            pos = array([0., 1., 0.5, 0.25, 0.75])
            color = array([[0, 255, 255, 255],
                           [255, 255, 0, 255],
                           [0, 0, 0, 255],
                           [0, 0, 255, 255],
                           [255, 0, 0, 255]], dtype=ubyte)
            super().__init__(pos, color)


class Viz():

    def _repr_png_(self):
        """This is used by ipython to plot inline.
        """
        self._widget.hide()
        QApplication.processEvents()

        try:
            self.image = QImage(self._widget.viewRect().size().toSize(),
                                QImage.Format_RGB32)
        except AttributeError:
            self._widget.updateGL()
            self.image = self._widget.grabFrameBuffer()

        painter = QPainter(self.image)
        self._widget.render(painter)

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.ReadWrite)
        self.image.save(buffer, 'PNG')
        buffer.close()

        return bytes(byte_array)
