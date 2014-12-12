"""Module with helper functions for plotting

"""
from logging import getLogger
lg = getLogger('phypno')

from vispy.color.colormap import get_colormap


def convert_color(dat, colormap):
    cmap = get_colormap(colormap)
    img_data = cmap[dat.flatten()].rgba
    return img_data.reshape(dat.shape + (4, ))
