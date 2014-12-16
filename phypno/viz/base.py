"""Module with helper functions for plotting

"""
from logging import getLogger
lg = getLogger('phypno')

from . import toolkit
if toolkit == 'visvis':
    from visvis import getframe

elif toolkit == 'vispy':

    from vispy.color.colormap import get_colormap, _colormaps, Colormap

    custom_cmap = {'jet': Colormap([(0, 0, .5), (0, 0, 1), (0, .5, 1), (0, 1, 1),
                                    (.5, 1, .5), (1, 1, 0), (1, .5, 0), (1, 0, 0),
                                    (.5, 0, 0)])}
    _colormaps.update(custom_cmap)


from vispy.io.image import _make_png


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
        It uses _make_png, which is a private function. Otherwise it needs to
        write to file and read from file.
        """
        if toolkit == 'visvis':
            self._canvas.DrawNow()
            image = getframe(self._viewbox)
            image[image < 0] = 0
            image[image > 1] = 1
            image = (image * 255).astype('uint8')
            self._canvas.Destroy()

        elif toolkit == 'vispy':
            self._canvas.show()
            image = self._canvas.render()
            self._canvas.close()

        img = _make_png(image).tobytes()

        return img
