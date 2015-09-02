"""Module to plot all the elements in 3d space.
"""
from numpy import max, mean, min
from vispy.color import get_colormap
from vispy.geometry import create_sphere, MeshData
from vispy.visuals.transforms import STTransform

from .base import normalize, SimpleMesh, Viz


CHAN_COLOR = 0., 1, 0, 1.
SKIN_COLOR = 0.94, 0.82, 0.81, 1.

SCALE_FACTOR = 135
ELEVATION = 0


class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes

    There is only one plot, so we define it at the __init__
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._plt = self._fig[0, 0]
        self._plt._configure_3d()

        # remove white space around the main plot
        self._plt.grid.margin = 0
        self._plt.title.stretch = 0, 0

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

        self._plt.view.add(mesh)

        surf_center = mean(surf.vert, axis=0)
        if surf_center[0] < 0:
            azimuth = 270
        else:
            azimuth = 90

        self._plt.view.camera.center = surf_center
        self._plt.view.camera.scale_factor = SCALE_FACTOR
        self._plt.view.camera.elevation = ELEVATION
        self._plt.view.camera.azimuth = azimuth

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
        chan_colors : ndarray
            array with colors for each channel
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

        for i, one_chan in enumerate(chan.chan):
            if chan_colors is not None:
                chan_color = chan_colors[i, :]
            else:
                chan_color = color

            mesh = SimpleMesh(meshdata, chan_color)
            mesh.transform = STTransform(translate=one_chan.xyz)
            self._plt.view.add(mesh)
