"""Module with helper functions for plotting

"""
from numpy import array, ubyte, linspace, c_, r_, zeros, arange
from PyQt4.Qt import QImage, QPainter, QBuffer, QIODevice, QByteArray
from PyQt4.QtGui import QApplication
from pyqtgraph import ColorMap


class Colormap(ColorMap):

    def __init__(self, name='jet', limits=(0, 1)):
        if name == 'jet':
            pos = linspace(limits[0], limits[1], 511)
            r = r_[zeros(255), arange(0, 256)]
            g = r_[arange(0, 255), arange(255, -1, -1)]
            b = r_[arange(255, 0, -1), zeros(256)]
            color = array(c_[r, g, b]) / 255

            super().__init__(pos, color)


class Viz():

    @property
    def size(self):
        return self._widget.size().width(), self._widget.size().height()

    @size.setter
    def size(self, newsize):
        self._widget.resize(*newsize)

    def _repr_png_(self):
        """This is used by ipython to plot inline.
        """
        self._widget.hide()
        QApplication.processEvents()

        try:
            self.image = QImage(self._widget.viewRect().size().toSize(),
                                QImage.Format_RGB32)
        except AttributeError:
            print('c')
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
