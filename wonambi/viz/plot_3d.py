"""Module to plot all the elements in 3d space.
"""
from numpy import array, isnan, linspace, max, min, nanmax, nanmin, r_
from vispy.color import get_colormap, ColorArray
from vispy.geometry import MeshData
from vispy.scene import TurntableCamera
from vispy.scene.visuals import Markers

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
                 values=None, limits_c=None, colormap=COLORMAP, alpha=1):
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
        """
        if color is not None and len(color) == 3:
            color = r_[array(color), float(alpha)]  # make sure it's an array

        if values is not None:
            if limits_c is None:
                limits_c = nanmin(values), nanmax(values)

            norm_values = normalize(values, *limits_c)

            cm = get_colormap(colormap)
            vertex_colors = cm[norm_values].rgba

            hasnan = isnan(vertex_colors).all(axis=1)
            vertex_colors[hasnan, :] = color

        if vertex_colors is not None:
            color = None

        meshdata = MeshData(vertices=surf.vert, faces=surf.tri,
                            vertex_colors=vertex_colors)
        mesh = SurfaceMesh(meshdata, color)

        self._add_mesh(mesh)
        self._surf.append(mesh)

    def add_chan(self, chan, color=None, values=None, limits_c=None, colormap=CHAN_COLORMAP, alpha=None):
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
        """
        # reuse previous limits
        if limits_c is None and self._chan_limits is not None:
            limits_c = self._chan_limits
            
        chan_colors, limits = _prepare_chan_colors(chan=chan, color=color, values=values, limits_c=limits_c, colormap=colormap, alpha=alpha)
        
        self._chan_limits = limits

        xyz = chan.return_xyz()
        marker = Markers()
        marker.set_data(pos=xyz, size=CHAN_SIZE, face_color=chan_colors)
        self._add_mesh(marker)


def _prepare_chan_colors(chan, color, values, limits_c, colormap, alpha):
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

    Returns
    -------
    1d / 2d array
        colors for all the channels or for each channel individually
    tuple of two float or None
        limits for the values
    """
    if values is not None:
        if limits_c is None:
            limits_c = min(values), max(values)

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
