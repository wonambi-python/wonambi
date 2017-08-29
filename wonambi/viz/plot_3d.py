"""Module to plot all the elements in 3d space.
"""
from numpy import array, isnan, max, mean, min, nanmax, nanmin, r_
from vispy.color import get_colormap
from vispy.geometry import create_sphere, MeshData
from vispy.visuals.transforms import STTransform

from vispy.scene import SceneCanvas, TurntableCamera
from vispy.visuals import Visual
from vispy.scene.visuals import create_visual_node
from vispy.geometry import create_sphere, MeshData
from numpy import array, clip, float32, r_
from vispy.gloo import VertexBuffer

from .base import COLORMAP, normalize, Viz
from .visuals import SurfaceMesh


CHAN_COLOR = 0., 1, 0, 1.
SKIN_COLOR = 0.94, 0.82, 0.81, 1.

SCALE_FACTOR = 150
ELEVATION = 0


class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes
    """
    _surf = []
    _chan = []

    _chan_colormap = None
    _chan_limits_c = None

    def __init__(self):
        super().__init__()
        self._view.camera = TurntableCamera(fov=0,
                                            elevation=ELEVATION, 
                                            azimuth=90, 
                                            scale_factor=SCALE_FACTOR)

    def add_surf(self, surf, color=SKIN_COLOR, vertex_colors=None,
                 values=None, limits_c=None, colormap=COLORMAP):
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
        """
        if color is not None and len(color) == 3:
            color = r_[array(color), 1.]  # make sure it's an array

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

    def add_chan(self, chan, color=CHAN_COLOR, chan_colors=None,
                 values=None, limits_c=None, colormap='coolwarm',
                 shift=(0, 0, 0)):
        """Add channels to visualization

        Parameters
        ----------
        chan : instance of Channels
            channels to plot
        color : tuple
            3-, 4-element tuple, representing RGB and alpha, between 0 and 1
        chan_colors : ndarray
            array with colors for each channel
        values : ndarray
            array with values for each channel
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy
        shift : tuple of 3 floats
            shift all electrodes by this amount (unit and order depend on
            xyz coordinates of the electrodes)
        """
        # larger if colors are meaningful
        if values is not None:
            meshdata = create_sphere(radius=3, method='ico')
        else:
            meshdata = create_sphere(radius=1.5, method='ico')

        chan_colors, limits = _prepare_chan_colors(color, chan_colors, values,
                                                   limits_c, colormap)

        # store values in case we update the values
        self._chan_colormap = colormap
        self._chan_limits_c = limits

        for i, one_chan in enumerate(chan.chan):
            if chan_colors.ndim == 2:
                chan_color = chan_colors[i, :]
            else:
                chan_color = chan_colors

            mesh = SimpleMesh(meshdata, chan_color)
            mesh.transform = STTransform(translate=one_chan.xyz + shift)
            self._plt.view.add(mesh)
            self._chan.append(mesh)


def _prepare_chan_colors(color, chan_colors, values, limits_c, colormap):
    """Return colors for all the channels based on various inputs.

    Parameters
    ----------
    color : tuple
        3-, 4-element tuple, representing RGB and alpha, between 0 and 1
    chan_colors : ndarray
        array with colors for each channel
    values : ndarray
        array with values for each channel
    limits_c : tuple of 2 floats, optional
        min and max values to normalize the color
    colormap : str
        one of the colormaps in vispy

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
        colors = cm[norm_values].rgba

    else:
        colors = array(color)   # make sure it's an array
        if len(colors) == 3:
            colors = r_[colors, 1.]

    return colors, limits_c

