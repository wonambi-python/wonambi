"""Module with helper functions for plotting
"""
from vispy.app import Application
from PyQt5.QtWidgets import QApplication
app = Application('pyqt5')


from vispy.scene import SceneCanvas, TurntableCamera
from vispy.visuals import Visual
from vispy.scene.visuals import create_visual_node
from vispy.geometry import create_sphere, MeshData
from numpy import array, clip, float32, r_
from vispy.gloo import VertexBuffer
from vispy.io.image import _make_png
from vispy.gloo.wrappers import read_pixels

COLORMAP = 'coolwarm'


class Viz(SceneCanvas):
    _view = None

    def __init__(self):
        super().__init__(keys='interactive', show=True, bgcolor='white')
        self._view = self.central_widget.add_view()

    def _add_mesh(self, mesh):
        self._view.add(mesh)

    def _repr_png_(self):
        """This is used by ipython to plot inline.
        """
        app.process_events()
        QApplication.processEvents()

        img = read_pixels()
        return bytes(_make_png(img))

    def save(self, png_file):
        """Save png to disk.

        Parameters
        ----------
        png_file : path to file
            file to write to

        Notes
        -----
        It relies on _repr_png_, so fix issues there.
        """
        with open(png_file, 'wb') as f:
            f.write(self._repr_png_())


def normalize(x, min_value, max_value):
    """Normalize value between min and max values.
    It also clips the values, so that you cannot have values higher or lower
    than 0 - 1."""
    x = (x - min_value) / (max_value - min_value)
    return clip(x, 0, 1)
