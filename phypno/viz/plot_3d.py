"""Module to plot all the elements in 3d space.

"""
from logging import getLogger
lg = getLogger('phypno')

from itertools import chain
from multiprocessing import Pool
from os import listdir, remove
from os.path import join, splitext
from subprocess import call
from tempfile import mkdtemp
from functools import partial

from numpy import dot, max, mean, min, ones
from numpy import asarray, NaN, empty, count_nonzero, isnan
from numpy.linalg import norm
from visvis import Mesh, gca, figure, solidSphere, CM_JET, record


CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255., 1)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255., 0.5)


class Viz3:
    """

    Attributes
    ----------
    _fig : instance of Figure
        current figure
    _ax : instance of Axes
        current axes
    """

    def __init__(self):
        self.xyz2surf = None

        self._fig = figure()
        self._ax = gca()
        self._ax.wobjects[0].Destroy()  # get rid of axises

        self._surf = None
        self._h_surf = None
        self._h_chan = []

    def add_surf(self, surf, color=SKIN_COLOR, xyz=None, values=None,
                 limits=None, colormap=CM_JET):

        if values is not None and limits is None:
            limits = (min(values), max(values))

        m = Mesh(self._ax, vertices=surf.vert, faces=surf.tri)

        if values is not None:
            if self.xyz2surf is None:
                lg.info('Computing transformation, it will take a while')
                self.xyz2surf = calc_xyz2surf(self._surf, xyz)

            m.SetValues(dot(self.xyz2surf, values))
            m.clim = limits
        else:
            m.faceColor = color
        m.colormap = colormap

        self._surf = surf
        self._h_surf = m
        self.center_surf()

    def add_chan(self, chan, color=(0, 0, 0, 1), values=None, limits=None,
                 colormap=CM_JET):
        """
        Parameters
        ----------
        chan : instance of phypno.attr.Channels
            channels to plot.
        color : tuple, optional
            4-element tuple, representing RGB and alpha.
        values : ndarray, optional
            vector with values for each electrode
        limits : 2 float values
            min and max values
        colormap : ndarray, optional
            2d matrix (for example, from visvis import CM_JET)
        """
        # larger if colors are meaningful
        if values is not None:
            SCALING = 3
        else:
            SCALING = 1.5

        if values is not None and limits is None:
            limits = (min(values), max(values))

        for i, one_chan in enumerate(chan.chan):
            s = solidSphere(list(one_chan.xyz), scaling=SCALING)

            if values is not None:
                _set_value_to_chan(s, values[i])
                s.clim = limits
            else:
                s.faceColor = color
            s.colormap = colormap

            self._h_chan.append(s)

    def update_surf(self, color=None, values=None, limits=None, colormap=None):
        """Plot values onto the brain surface.

        Parameters
        ----------
        values : numpy.ndarray
            1-d vector with values at each point.

        Notes
        -----
        The transformation matrix does the important part of converting the values
        at each electrode into the values onto the surface. You can specify it as
        you want, as long as its dimensions are number of vertices X number of
        values.

        """
        m = self._h_surf
        if values is not None:
            m.SetValues(dot(self.xyz2surf, values))

        if limits is not None:
            m.clim = limits

        if colormap is not None:
            m.colormap = colormap

        if color is not None:
            m.faceColor = color

    def update_chan(self, color=None, values=None, limits=None, colormap=None):

        for i, s in enumerate(self._h_chan):

            if values is not None:
                _set_value_to_chan(s, values[i])

            if limits is not None:
                s.clim = limits

            if colormap is not None:
                s.colormap = colormap

            if color is not None:
                s.faceColor = color

    def animate_surf(self, all_values, output_file):
        """I cannot modify frame rate in avconv, default is 24"""

        img_dir = mkdtemp()

        rec = record(self._ax)
        for values in all_values:
            self.update_surf(values=values)
            self._fig.DrawNow()
        rec.Stop()
        rec.Export(join(img_dir, 'image.png'))

        if splitext(output_file)[1] == '.gif':
            _make_gif(img_dir, output_file)
        else:
            _make_mp4(img_dir, output_file)

    def animate_chan(self, all_values, output_file):

        img_dir = mkdtemp()

        rec = record(self._ax)
        for values in all_values:
            self.update_chan(values=values)
            self._fig.DrawNow()
        rec.Stop()
        rec.Export(join(img_dir, 'image.png'))

        if splitext(output_file)[1] == '.gif':
            _make_gif(img_dir, output_file)
        else:
            _make_mp4(img_dir, output_file)

    def rotate(self, output_file, loop='full', step=5):
        """Create rotating images in a temporary folder.

        Parameters
        ----------
        fig : instance of visvis.Figure
            figure being plotted.
        loop : str, optional
            'full' (complete rotation) or 'patrol' (half rotation)
        step : int, optional
            distance in degrees between frames
        focus : str, optional
            'fig' or 'axis', which part of the image should be saved
        poster : bool, optional
            make a poster image before the video (it creates "poster.png")

        Returns
        -------
        path to dir
            temporary directory with images

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

        rec = record(self._ax)
        for i in angles:
            self._ax.camera.azimuth = i
            self._fig.DrawNow()

        rec.Stop()
        rec.Export(join(img_dir, 'image.png'))

        if splitext(output_file)[1] == '.gif':
            _make_gif(img_dir, output_file)
        else:
            _make_mp4(img_dir, output_file)

    def center_surf(self):
        center_surf = tuple(mean(self._surf.vert, axis=0))
        self._ax.camera.loc = center_surf
        self._ax.camera.elevation = 0
        self._ax.camera.zoom = 0.007

        if center_surf[0] > 0:  # right hemisphere
            self._ax.camera.azimuth = 90
        else:
            self._ax.camera.azimuth = 270

    def draw(self):
        pass


def calc_xyz2surf(surf, xyz, threshold=10):
    """Calculate transformation matrix from xyz values to vertices.

    Parameters
    ----------
    surf : instance of phypno.attr.Surf
        the surface of only one hemisphere.
    xyz : numpy.ndarray
        N x 3 matrix, with the locations in x, y, z.
    dist_func : function
        function used to calculate the distance.

    Returns
    -------
    numpy.ndarray
        nVertices X xyz.shape[0] matrix

    Notes
    -----
    This function is a helper to plot_values_on_surf, by creating a
    transformation matrix from the values in space (f.e. at each electrode) to
    the position of the vertices (used to show the brain surface).

    There are many ways to move from values to vertices. You can either create
    your own matrix (and skip calculate_chan2surf_trans altogether) or you can
    pass a function to calculate_chan2surf_trans. The "dist_func" takes two
    parameters: the first is the xyz position of one vertex, the second is the
    xyz position of one electrode (i.e. a row of the parameter "xyz").
    Because it's a loop over all the vertices, this function is pretty slow,
    but if you calculate it once, you can reuse it.

    """
    with Pool() as p:
        xyz2surf = p.map(partial(calc_one_vert, xyz=xyz, thres=threshold),
                         surf.vert)

    xyz2surf = asarray(xyz2surf)
    xyz2surf[isnan(xyz2surf)] = 0

    return xyz2surf


def calc_one_vert(one_vert, xyz=None, thres=10):
    trans = empty(xyz.shape[0])
    for i, one_xyz in enumerate(xyz):
        if norm(one_vert - one_xyz) <= thres:
            trans[i] = 1
        else:
            trans[i] = NaN
    return trans / count_nonzero(~isnan(trans))


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
    fig : instance of visvis.Figure
        figure being plotted.
    gif_file : path to file
        file where you want to save the gif
    loop : str, optional
        'full' (complete rotation) or 'patrol' (half rotation)
    step : int
        distance in degrees between frames
    focus : str
        'fig' or 'axis', which part of the image should be saved

    Notes
    -----
    It requires ''convert'' from Imagemagick
    """
    call('convert ' + join(img_dir, 'image*.png') + ' ' + gif_file,
         shell=True)


def _make_mp4(img_dir, movie_file):
    """Save the image as rotating movie.

    Parameters
    ----------
    fig : instance of visvis.Figure
        figure being plotted.
    movie_file : path to file
        file where you want to save the movie
    loop : str, optional
        'full' (complete rotation) or 'hemi' (half rotation) or 'patrol' (half
        rotation in two directions) or 'consistent' (like hemi, but in the same
        direction for both hemispheres)
    step : int
        distance in degrees between frames
    focus : str
        'fig' or 'axis', which part of the image should be saved
    poster : bool, optional
        make a poster image before the video (it creates "poster.png")

    Notes
    -----
    It requires ''avconv'' from LibAv

    """
    # name in the images depends on the number of images
    # I took this part from visvis directly
    N = len(listdir(img_dir))
    formatter = '%04d'
    if N < 10:
        formatter = '%d'
    elif N < 100:
        formatter = '%02d'
    elif N < 1000:
        formatter = '%03d'

    try:
        remove(movie_file)
    except FileNotFoundError:
        pass

    call('avconv -i ' + join(img_dir, 'image' + formatter + '.png') +
         ' -tune animation ' + movie_file, shell=True)
