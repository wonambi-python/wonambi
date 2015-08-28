"""Module to plot all the elements in 3d space.
"""
from numpy import max, mean, min
from vispy.color import get_colormap
from vispy.geometry import create_sphere, MeshData
from vispy.plot import Fig
from vispy.visuals.transforms import STTransform

from .base import normalize, SimpleMesh, Viz


CHAN_COLOR = 0., 1, 0, 1.
SKIN_COLOR = 0.94, 0.82, 0.81, 1.

SCALE_FACTOR = 135
ELEVATION = 0


class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes
    """
    def __init__(self, color='wk'):
        self._color = color

        self._fig = Fig()
        f = self._fig[0, 0]
        f._configure_3d()

        self._limits_x = None  # tuple
        self._limits_y = None  # tuple

    def add_surf(self, surf, color=SKIN_COLOR, vertex_colors=None,
                 values=None, limits_c=None, colormap='coolwarm'):
        """Add surfaces to the visualization.

        Parameters
        ----------
        surf : instance of phypno.attr.anat.Surf
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
        if values is not None:
            if limits_c is None:
                limits_c = min(values), max(values)

            norm_values = normalize(values, *limits_c)

            cm = get_colormap(colormap)
            vertex_colors = cm[norm_values].rgba  # TODO: NaN

        if vertex_colors is not None:
            color = None

        meshdata = MeshData(vertices=surf.vert, faces=surf.tri,
                            vertex_colors=vertex_colors)
        mesh = SimpleMesh(meshdata, color)

        f = self._fig[0, 0]
        f.view.add(mesh)

        surf_center = mean(surf.vert, axis=0)
        if surf_center[0] < 0:
            azimuth = 270
        else:
            azimuth = 90

        f.view.camera.azimuth = azimuth
        f.view.camera.center = surf_center
        f.view.camera.scale_factor = SCALE_FACTOR
        f.view.camera.elevation = ELEVATION

        self._mesh = mesh

    def add_chan(self, chan, color=CHAN_COLOR, chan_colors=None,
                 values=None, limits_c=None, colormap='coolwarm'):
        """Add channels to visualization

        Parameters
        ----------
        chan : instance of Channels
            channels to plot
        color : tuple
            4-element tuple, representing RGB and alpha, between 0 and 1
        values : ndarray
            array with values for each channel
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy
        """
        if values is not None:
            if limits_c is None:
                limits_c = min(values), max(values)

            norm_values = normalize(values, *limits_c)

            cm = get_colormap(colormap)
            chan_colors = cm[norm_values].rgba

            color = None

        # larger if colors are meaningful
        if values is not None:
            meshdata = create_sphere(radius=3, method='ico')
        else:
            meshdata = create_sphere(radius=1.5, method='ico')

        f = self._fig[0, 0]

        for i, one_chan in enumerate(chan.chan):
            if chan_colors is not None:
                chan_color = chan_colors[i, :]
            else:
                chan_color = color

            mesh = SimpleMesh(meshdata, chan_color)
            mesh.transform = STTransform(translate=one_chan.xyz)
            f.view.add(mesh)
