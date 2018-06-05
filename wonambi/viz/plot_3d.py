"""Module to plot all the elements in 3d space.
"""
from numpy import (linspace,
                   nanmax,
                   mean,
                   tile,
                   array,
                   abs,
                   )
from vispy.color import get_colormap, ColorArray
from vispy.geometry import MeshData
from vispy.scene import TurntableCamera
from vispy.scene.visuals import Markers, ColorBar
from vispy.visuals.transforms import MatrixTransform

from .base import COLORMAP, normalize, Viz
from .visuals import SurfaceMesh
from ..attr.chan import find_channel_groups


SKIN_COLOR = 0.94, 0.82, 0.81
CHAN_SIZE = 15
CHAN_COLORMAP = 'coolwarm'

SCALE_FACTOR = 150
ELEVATION = 0


class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes
    """
    _surf = []
    _chan_limits = None

    def __init__(self):
        super().__init__()
        self._view.camera = TurntableCamera(fov=0,
                                            elevation=ELEVATION,
                                            azimuth=-90,
                                            scale_factor=SCALE_FACTOR)

    def add_surf(self, surf, color=SKIN_COLOR, vertex_colors=None,
                 values=None, limits_c=None, colormap=COLORMAP, alpha=1,
                 colorbar=False):
        """Add surfaces to the visualization.

        Parameters
        ----------
        surf : instance of wonambi.attr.anat.Surf
            surface to be plotted
        color : tuple or ndarray, optional
            4-element tuple, representing RGB and alpha, between 0 and 1
        vertex_colors : ndarray
            ndarray with n vertices x 4 to specify color of each vertex
        values : ndarray, optional
            vector with values for each vertex
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy
        alpha : float
            transparency (1 = opaque)
        colorbar : bool
            add a colorbar at the back of the surface
        """
        colors, limits = _prepare_colors(color=color, values=values,
                                         limits_c=limits_c, colormap=colormap,
                                         alpha=alpha)

        # meshdata uses numpy array, in the correct dimension
        vertex_colors = colors.rgba
        if vertex_colors.shape[0] == 1:
            vertex_colors = tile(vertex_colors, (surf.n_vert, 1))

        meshdata = MeshData(vertices=surf.vert, faces=surf.tri,
                            vertex_colors=vertex_colors)
        mesh = SurfaceMesh(meshdata)

        self._add_mesh(mesh)

        # adjust camera
        surf_center = mean(surf.vert, axis=0)
        if surf_center[0] < 0:
            azimuth = 270
        else:
            azimuth = 90
        self._view.camera.azimuth = azimuth
        self._view.camera.center = surf_center

        self._surf.append(mesh)

        if colorbar:
            self._view.add(_colorbar_for_surf(colormap, limits))

    def add_chan(self, chan, color=None, values=None, limits_c=None,
                 colormap=CHAN_COLORMAP, alpha=None, colorbar=False):
        """Add channels to visualization

        Parameters
        ----------
        chan : instance of Channels
            channels to plot
        color : tuple
            3-, 4-element tuple, representing RGB and alpha, between 0 and 1
        values : ndarray
            array with values for each channel
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy
        alpha : float
            transparency (0 = transparent, 1 = opaque)
        colorbar : bool
            add a colorbar at the back of the surface
        """
        # reuse previous limits
        if limits_c is None and self._chan_limits is not None:
            limits_c = self._chan_limits

        chan_colors, limits = _prepare_colors(color=color, values=values,
                                              limits_c=limits_c,
                                              colormap=colormap, alpha=alpha,
                                              chan=chan)

        self._chan_limits = limits

        xyz = chan.return_xyz()
        marker = Markers()
        marker.set_data(pos=xyz, size=CHAN_SIZE, face_color=chan_colors)
        self._add_mesh(marker)

        if colorbar:
            self._view.add(_colorbar_for_surf(colormap, limits))


def _colorbar_for_surf(colormap, limits):
    colorbar = ColorBar(colormap, 'top', (50, 10), clim=limits)
    tr = MatrixTransform()
    tr.rotate(-90, (0, 1, 0))
    tr.translate((0, -100, 50))
    colorbar.transform = tr

    return colorbar


def _prepare_colors(color, values, limits_c, colormap, alpha, chan=None):
    """Return colors for all the channels based on various inputs.

    Parameters
    ----------
    color : tuple
        3-, 4-element tuple, representing RGB and alpha, between 0 and 1
    values : ndarray
        array with values for each channel
    limits_c : tuple of 2 floats, optional
        min and max values to normalize the color
    colormap : str
        one of the colormaps in vispy
    alpha : float
        transparency (0 = transparent, 1 = opaque)
    chan : instance of Channels
        use labels to create channel groups

    Returns
    -------
    1d / 2d array
        colors for all the channels or for each channel individually
    tuple of two float or None
        limits for the values
    """
    if values is not None:
        if limits_c is None:
            limits_c = array([-1, 1]) * nanmax(abs(values))

        norm_values = normalize(values, *limits_c)

        cm = get_colormap(colormap)
        colors = cm[norm_values]

    elif color is not None:
        colors = ColorArray(color)

    else:
        cm = get_colormap('hsl')
        group_idx = _chan_groups_to_index(chan)
        colors = cm[group_idx]

    if alpha is not None:
        colors.alpha = alpha

    return colors, limits_c


def _chan_groups_to_index(chan):

    groups = find_channel_groups(chan)
    n_groups = len(groups)
    idx = linspace(0, 1, n_groups)
    group_idx = chan.return_label()
    for i, labels in enumerate(groups.values()):
        group_idx = [idx[i] if label in labels else label for label in group_idx]

    return group_idx
