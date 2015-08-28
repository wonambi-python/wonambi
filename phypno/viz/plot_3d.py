"""Module to plot all the elements in 3d space.
"""
from numpy import array, isnan, max, mean, min, tile
from vispy.geometry import MeshData
from vispy.plot import Fig

from .base import Viz, Colormap, BrainMesh

CHAN_COLOR = 0, 255, 0, 255
SKIN_COLOR = (0.94, 0.82, 0.81, 1.)

SCALE_FACTOR = 130
ELEVATION = 0




class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes
    """
    def __init__(self, color='wk'):
        self._color = color

        self._fig = Fig()

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
        vertex_colors : ndarray, optional
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

            colormap = Colormap(name=colormap, limits=limits_c)
            vertexColors = colormap.mapToFloat(values)
            vertexColors[isnan(values)] = color

        if color is None and vertex_colors is None:
            color = SKIN_COLOR

        meshdata = MeshData(vertices=surf.vert, faces=surf.tri,
                            vertex_colors=c_[norma(surf.vert[:, 0]), ones(surf.vert.shape[0]), ones(surf.vert.shape[0]), ones(surf.vert.shape[0])])
        mesh = BrainMesh(meshdata)

        f = self._fig[0, 0]
        f._configure_3d()
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

    def add_chan(self, chan, color=CHAN_COLOR, values=None, limits_c=None,
                 colormap='coolwarm'):
        """Add channels to visualization

        Parameters
        ----------
        chan : instance of Channels
            channels to plot
        color : tuple
            4-element tuple, representing RGB and alpha, between 0 and 255
        values : ndarray
            array with values for each channel
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy
        """
        color = array(color) / 255

        if values is not None:
            if limits_c is None:
                limits_c = min(values), max(values)

            colormap = Colormap(name=colormap, limits=limits_c)
            vertexColors = colormap.mapToFloat(values)
            vertexColors[isnan(values)] = color
        else:
            vertexColors = tile(color, (chan.n_chan, 1))

        # larger if colors are meaningful
        if values is not None:
            radius = 3
        else:
            radius = 1.5

        for i, one_chan in enumerate(chan.chan):
            sphere = MeshData.sphere(10, 10, radius=radius)
            sphere.setVertexColors(tile(vertexColors[i, :],
                                        (sphere._vertexes.shape[0], 1)))

            mesh = GLMeshItem(meshdata=sphere, smooth=True,
                              shader='shaded', glOptions='translucent')

            mesh.translate(*one_chan.xyz)

            self._widget.addItem(mesh)
        self._widget.show()
