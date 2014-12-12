"""Module to plot all the elements in 3d space.

"""
from logging import getLogger
lg = getLogger('phypno')

from itertools import chain
from os import remove
from os.path import join, splitext
from subprocess import call
from tempfile import mkdtemp

from numpy import max, mean, min, ones

from vispy.geometry import MeshData, create_sphere
from vispy.scene import SceneCanvas
from vispy.scene.visuals import Mesh
from vispy.visuals.transforms import STTransform

from .base import convert_color, Viz

CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255., 1)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255., 0.5)
SHADING = 'smooth'
CAMERA = 'perspective'
DISTANCE = 400  # if it's too close, it's all deformed

IMAGE = 'image%09d.jpg'


class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes

    Attributes
    ----------
    xyz2surf : ndarray
        nVertices X nChan matrix, that explains how channel activity should be
        plotted onto the vertices

    _canvas : instance of Canvas
        current figure

    """
    def __init__(self):
        self._canvas = SceneCanvas(keys='interactive')

        self._viewbox = None
        self._mesh = None
        self._chan = []

        self._surf_limits_c = None
        self._chan_limits_c = None
        self._colormap = None

    def add_surf(self, surf, color=SKIN_COLOR, values=None, limits_c=None,
                 colormap='cool'):
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

        meshdata = MeshData(vertices=surf.vert, faces=surf.tri)
        mesh = Mesh(meshdata=meshdata, color=color, shading='smooth')

        viewbox = self._canvas.central_widget.add_view()
        viewbox.set_camera('turntable', mode=CAMERA, azimuth=90,
                           distance=DISTANCE, center=-mean(surf.vert, axis=0))
        viewbox.add(mesh)

        if values is not None:
            if limits_c is None:
                min_c = min(values)  # maybe NaN here
                max_c = max(values)
            else:
                min_c, max_c = limits_c

            self._surf_limits_c = min_c, max_c
            self._colormap = colormap
            values = (values - min_c) / (max_c - min_c)
            meshdata.set_vertex_colors(convert_color(values, colormap))

        self._mesh = mesh
        self._viewbox = viewbox

        self._canvas.show()

    def add_chan(self, chan, color=(0, 1, 0, 1), values=None, limits_c=None,
                 colormap='cool'):
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
            colors = convert_color(values, colormap)
        else:
            colors = [color] * chan.n_chan

        for one_chan, one_color in zip(chan.chan, colors):
            mesh = Mesh(meshdata=sphere, color=one_color, shading='smooth')
            mesh.transform = STTransform(translate=one_chan.xyz)
            viewbox.add(mesh)

        self._canvas.show()

    def update_surf(self, values):
        """Change values of the brain surface.

        THIS DOES NOT WORK CURRENTLY. It updates if you change the values
        before the figure appears.

        Parameters
        ----------
        values : ndarray, optional
            vector with values for each channel

        Notes
        -----
        It reuses the color-limits and color map of the initial surf
        """
        min_c, max_c = self._surf_limits_c
        values = (values - min_c) / (max_c - min_c)
        self._mesh.mesh_data.set_vertex_colors(convert_color(values,
                                                             self._colormap))

    def update_chan(self, values):
        """Change values of the electrodes.

        Parameters
        ----------
        values : ndarray, optional
            vector with values for each channel

        BROKEN
        """
        min_c, max_c = self._surf_limits_c
        values = (values - min_c) / (max_c - min_c)

    def animate_surf(self, all_values, output_file):
        """Create a movie with the changing values onto the surface.

        Parameters
        ----------
        all_values : ndarray
            nTime X nChan matrix, it will loop over time
        output_file : str
            path to file, it can end in '.gif' or in any format used by avconv

        Notes
        -----
        It needs 'avconv' to be installed.
        I cannot modify frame rate in avconv, default is 24. Lots of options
        but I don't know how to use them.
        """
        img_dir = mkdtemp()

        for i, values in enumerate(all_values):
            self.update_surf(values=values)
            self._fig.DrawNow()
            screenshot(join(img_dir, IMAGE % i), self._fig, sf=1)

        if splitext(output_file)[1] == '.gif':
            _make_gif(img_dir, output_file)
        else:
            _make_mp4(img_dir, output_file)

    def animate_chan(self, all_values, output_file):
        """Create a movie with the changing values of the electrodes.

        Parameters
        ----------
        all_values : ndarray
            nTime X nChan matrix, it will loop over time
        output_file : str
            path to file, it can end in '.gif' or in any format used by avconv

        Notes
        -----
        It needs 'avconv' to be installed.
        I cannot modify frame rate in avconv, default is 24. Lots of options
        but I don't know how to use them.
        """
        img_dir = mkdtemp()

        for i, values in enumerate(all_values):
            self.update_chan(values=values)
            self._fig.DrawNow()
            screenshot(join(img_dir, IMAGE % i), self._fig, sf=1)

        if splitext(output_file)[1] == '.gif':
            _make_gif(img_dir, output_file)
        else:
            _make_mp4(img_dir, output_file)

    def rotate(self, output_file, loop='full', step=5):
        """Create rotating images in a temporary folder.

        Parameters
        ----------
        output_file : str
            path to file, it can end in '.gif' or in any format used by avconv
        loop : str, optional
            'full' (complete rotation) or 'hemi' (half rotation) or
            'consistent' (but both hemispheres have the same direction) or
            'patrol' (half rotation back and forth)
        step : int, optional
            distance in degrees between frames
        """
        img_dir = mkdtemp()

        if self._ax.camera.azimuth > 0:  # right hemi
            if loop == 'hemi':
                angles = range(180, 0, -step)
            elif loop == 'full':
                angles = range(180, -180, -step)
            elif loop == 'patrol':
                angles = chain(range(180, 0, -step),
                               range(0, 180, step))
            elif loop == 'consistent':
                angles = range(180, 0, -step)

        else:
            if loop == 'hemi':
                angles = range(-180, 0, step)
            elif loop == 'full':
                angles = range(-180, 180, step)
            elif loop == 'patrol':
                angles = chain(range(-180, 0, step),
                               range(0, -180, -step))
            elif loop == 'consistent':
                angles = range(0, -180, -step)

        for i, ang in enumerate(angles):
            self._ax.camera.azimuth = ang
            self._fig.DrawNow()
            screenshot(join(img_dir, IMAGE % i), self._fig, sf=1)

        if splitext(output_file)[1] == '.gif':
            _make_gif(img_dir, output_file)
        else:
            _make_mp4(img_dir, output_file)

    def center_surf(self):
        """Center the figure by looking at the side of the hemisphere."""
        center_surf = tuple(mean(self._surf.vert, axis=0))
        self._ax.camera.loc = center_surf
        self._ax.camera.elevation = 0
        self._ax.camera.zoom = 0.007

        if center_surf[0] > 0:  # right hemisphere
            self._ax.camera.azimuth = 90
        else:
            self._ax.camera.azimuth = 270


def _set_value_to_chan(s, v):
    """Change color for one channel. Each dot is actually a complicated mesh,
    so we need to change the color of all the elements.

    Parameters
    ----------
    s : instance of solidSphere
        the representation of the channel
    v : float
        value to assign to the channel.
    """
    n_vert = s._vertices.shape[0]
    s.SetValues(v * ones((n_vert, 1)))


def _make_gif(img_dir, gif_file):
    """Save the image as rotating gif.

    Parameters
    ----------
    img_dir : path to dir
        directory with all the imags
    gif_file : path to file
        file where you want to save the gif

    Notes
    -----
    It requires ''convert'' from Imagemagick
    """
    call('convert ' + join(img_dir, 'image*.jpg') + ' ' + gif_file,
         shell=True)


def _make_mp4(img_dir, movie_file):
    """Save the image as rotating movie.

    Parameters
    ----------
    img_dir : path to dir
        directory with all the imags
    movie_file : path to file
        file where you want to save the movie

    Notes
    -----
    It requires ''avconv'' from LibAv
    """
    try:
        remove(movie_file)
    except FileNotFoundError:
        pass

    call('avconv -i ' + join(img_dir, IMAGE) +
         ' -tune animation ' + movie_file, shell=True)
