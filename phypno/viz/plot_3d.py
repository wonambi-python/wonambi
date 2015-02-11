"""Module to plot all the elements in 3d space.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import max, mean, min, ones

from . import toolkit

if toolkit == 'visvis':
    from visvis import Mesh, gca, figure, solidSphere, CM_JET
    ELEVATION = 0
    ZOOM = 0.007

elif toolkit == 'vispy':
    from vispy.geometry import MeshData, create_sphere
    from vispy.scene import SceneCanvas
    from vispy.scene.visuals import Mesh
    from vispy.visuals.transforms import STTransform
    SHADING = 'smooth'
    CAMERA = 'perspective'
    DISTANCE = 150  # only works for perspective, but it looks funny

from .base import convert_color, Viz

CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255., 1)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255., 0.5)


class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes

    Attributes
    ----------
    _canvas : instance of Canvas
        current figure

    """
    def __init__(self):
        if toolkit == 'visvis':
            self._canvas = figure()
            self._viewbox = gca()
            self._viewbox.wobjects[0].Destroy()
        elif toolkit == 'vispy':
            self._canvas = SceneCanvas(keys='interactive')
            self._viewbox = None

        self._mesh = None
        self._chan = []

    def add_surf(self, surf, color=SKIN_COLOR, values=None, limits_c=None,
                 colormap='jet'):
        """Add surfaces to the visualization.

        Parameters
        ----------
        surf : instance of phypno.attr.anat.Surf
            surface to be plotted
        color : tuple, optional
            4-element tuple, representing RGB and alpha, between 0 and 1
        values : ndarray, optional
            vector with values for each vertex
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy

        Notes
        -----
        'color' vs 'xyz' and 'values' are mutally exclusive. You need to
        specify 'xyz' and 'values' if you use those.

        If you specify 'values', then you'll need a matrix called 'xyz2surf'
        that converts from the channel values to the electrodes.
        It takes a few seconds to compute but once it's done, plotting is
        really fast.
        You can pre-compute it (using arbitrary values) and pass it as
        attribute to this class.
        """
        if values is not None:
            color = None  # otherwise this color prevails
            if limits_c is None:
                min_c = min(values)  # maybe NaN here
                max_c = max(values)
            else:
                min_c, max_c = limits_c
            values = (values - min_c) / (max_c - min_c)

        surf_center = mean(surf.vert, axis=0)
        if surf_center[0] < 0:
            azimuth = 270
        else:
            azimuth = 90

        if toolkit == 'visvis':
            viewbox = self._viewbox
            mesh = Mesh(viewbox, vertices=surf.vert, faces=surf.tri)

            viewbox.camera.loc = tuple(surf_center)
            viewbox.camera.elevation = ELEVATION
            viewbox.camera.zoom = ZOOM
            viewbox.camera.azimuth = azimuth

            if values is not None:
                mesh.SetValues(values)
                mesh.clim = (0, 1)
                mesh.colormap = visvis_colormap(colormap)
            else:
                mesh.faceColor = color

        elif toolkit == 'vispy':
            meshdata = MeshData(vertices=surf.vert, faces=surf.tri)
            mesh = Mesh(meshdata=meshdata, color=color, shading='smooth')
            viewbox = self._canvas.central_widget.add_view()
            viewbox.add(mesh)

            viewbox.set_camera('turntable', mode=CAMERA, azimuth=azimuth,
                               distance=DISTANCE, center=-surf_center)

            if values is not None:
                meshdata.set_vertex_colors(convert_color(values, colormap))

            self._canvas.show()

        self._mesh = mesh
        self._viewbox = viewbox

    def add_chan(self, chan, color=(0, 1, 0, 1), values=None, limits_c=None,
                 colormap='jet'):
        """
        Parameters
        ----------
        chan : instance of phypno.attr.Channels
            channels to plot.
        color : tuple, optional
            4-element tuple, representing RGB and alpha, between 0 and 1
        values : ndarray, optional
            vector with values for each electrode
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy

        """
        # larger if colors are meaningful
        if values is not None:
            radius = 3
        else:
            radius = 1.5

        if toolkit == 'vispy':
            sphere = create_sphere(10, 10, radius=radius)

        if self._viewbox is not None:
            viewbox = self._viewbox
        else:
            viewbox = self._canvas.central_widget.add_view()
            viewbox.set_camera('turntable', mode=CAMERA, azimuth=90,
                               distance=DISTANCE)
            self._viewbox = viewbox

        if values is not None:
            if limits_c is None:
                min_c = min(values)  # maybe NaN here
                max_c = max(values)
            else:
                min_c, max_c = limits_c

            values = (values - min_c) / (max_c - min_c)
            if toolkit == 'visvis':
                colors = values
            elif toolkit == 'vispy':
                colors = convert_color(values, colormap)
        else:
            colors = [color] * chan.n_chan

        for one_chan, one_color in zip(chan.chan, colors):
            if toolkit == 'visvis':
                mesh = solidSphere(list(one_chan.xyz), scaling=radius)
                if values is not None:
                    n_vert = mesh._vertices.shape[0]
                    mesh.SetValues(one_color * ones((n_vert, 1)))
                    mesh.colormap = visvis_colormap(colormap)
                    mesh.clim = (0, 1)

                else:
                    mesh.faceColor = one_color

            elif toolkit == 'vispy':
                mesh = Mesh(meshdata=sphere, color=one_color, shading='smooth')
                mesh.transform = STTransform(translate=one_chan.xyz)
                viewbox.add(mesh)


def visvis_colormap(colormap):
    if colormap == 'jet':
        return CM_JET
    else:
        raise NotImplementedError('Only jet colormap for visvis')
