"""Module to plot all the elements in 3d space.

"""
from logging import getLogger
lg = getLogger('phypno')

from itertools import chain
from os import listdir, remove
from os.path import join, splitext
from shutil import copyfile
from subprocess import call
from tempfile import mkdtemp

from numpy import asarray, dot, hstack, max, mean, min, ones, zeros
from numpy.linalg import norm
from visvis import Mesh, gca, figure, solidSphere, CM_JET, record, screenshot


CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255.)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255.)


def plot_surf(surf, fig=None):
    """Plot channels in 3d space.

    Parameters
    ----------
    surf : instance of phypno.attr.Surf
        surface to plot (only one hemisphere).
    fig : instance of visvis.Figure, optional
        figure being plotted.

    Returns
    -------
    instance of visvis.Figure
        main figure

    """
    fig = _make_fig(fig)

    ax = fig.currentAxes
    m = Mesh(ax, vertices=surf.vert, faces=surf.tri)
    m.faceColor = hstack((asarray(SKIN_COLOR), 0.5))

    # center the image
    center_surf = tuple(mean(surf.vert, axis=0))
    ax.camera.loc = center_surf
    ax.camera.elevation = 0
    ax.camera.zoom = 0.007

    if center_surf[0] > 0:  # right hemisphere
        ax.camera.azimuth = 90
    else:
        ax.camera.azimuth = 270

    return fig


def plot_values_on_surf(surf, values, trans, fig=None):
    """Plot values onto the brain surface.

    Parameters
    ----------
    surf : instance of phypno.attr.Surf
        surface to plot (only one hemisphere).
    values : numpy.ndarray
        1-d vector with values at each point.
    trans : numpy.ndarray
        nVertices X nValues matrix
    fig : instance of visvis.Figure, optional
        figure being plotted.

    Returns
    -------
    instance of visvis.Figure
        main figure
    instance of visvis.Mesh
        mesh which can be modified afterwards

    Notes
    -----
    The transformation matrix does the important part of converting the values
    at each electrode into the values onto the surface. You can specify it as
    you want, as long as its dimensions are number of vertices X number of
    values.

    """
    fig = _make_fig(fig)

    ax = fig.currentAxes
    m = Mesh(ax, vertices=surf.vert, faces=surf.tri)
    m.SetValues(dot(trans, values), setClim=True)
    m.colormap = CM_JET

    return fig, m


def calculate_chan2surf_trans(surf, xyz, dist_func=None):
    """Calculate transformation matrix from channel values to vertices.

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
    if dist_func is None:
        dist_func = lambda one_vert, one_chan: 1 / norm(one_vert - one_chan)

    trans = zeros((surf.vert.shape[0], xyz.shape[0]))

    for i, one_vert in enumerate(surf.vert):
        for j, one_xyz in enumerate(xyz):
            trans[i, j] = dist_func(one_vert, one_xyz)

    return trans


def plot_chan(chan, fig=None, color=(0, 0, 0, 1), values=None, limits=None,
              colormap=CM_JET):
    """Plot channels in 3d space.

    Parameters
    ----------
    chan : instance of phypno.attr.Channels
        channels to plot.
    fig : instance of visvis.Figure, optional
        figure being plotted.
    color : tuple, optional
        4-element tuple, representing RGB and alpha.
    values : ndarray, optional
        vector with values for each electrode
    limits : 2 float values
        min and max values
    colormap : ndarray, optional
        2d matrix (for example, from visvis import CM_JET)

    Returns
    -------
    instance of visvis.Figure

    """
    fig = _make_fig(fig)
    azimuth = fig.currentAxes.camera.azimuth
    elevation = fig.currentAxes.camera.elevation
    zoom = fig.currentAxes.camera.zoom

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
            n_vert = s._vertices.shape[0]
            s.SetValues(values[i] * ones((n_vert, 1)))
            s.clim = limits
        else:
            s.faceColor = color
        s.colormap = colormap

    fig.currentAxes.camera.azimuth = azimuth
    fig.currentAxes.camera.elevation = elevation
    fig.currentAxes.camera.zoom = zoom

    return fig


def make_gif(fig, gif_file, loop='full', step=5, focus='fig'):
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
    img_dir = _rotate_images(fig, loop=loop, step=step, focus=focus)

    call('convert ' + join(img_dir, 'image*.png') + ' ' + gif_file,
         shell=True)


def make_movie(fig, movie_file, loop='full', step=5, focus='fig', rate=24,
               poster=False):
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
    img_dir = _rotate_images(fig, loop=loop, step=step, focus=focus,
                             poster=poster)

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
         ' -r ' + str(rate) + ' -tune animation ' + movie_file, shell=True)

    if poster:
        poster_file = splitext(movie_file)[0] + '_poster.jpg'
        copyfile(join(img_dir, 'poster.jpg'), poster_file)


def _make_fig(fig=None):
    """Create a figure, if it doesn't exist already.

    Parameters
    ----------
    fig : instance of visvis.Figure, optional
        figure being plotted.

    Returns
    -------
    instance of visvis.Figure

    """
    fig = figure(fig)
    ax = gca()
    ax.axis.visible = False

    return fig


def _rotate_images(fig, loop='full', step=5, focus='fig', poster=False):
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

    ax = fig.currentAxes
    if focus == 'fig':
        obj = fig
    elif focus == 'axis':
        obj = ax

    AZIMUTH = ax.camera.azimuth

    if ax.camera.azimuth > 0:  # right hemi
        poster_angle = 90
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
        poster_angle = -90
        if loop == 'hemi':
            angles = range(-180, 0, step)
        elif loop == 'full':
            angles = range(-180, 180, step)
        elif loop == 'patrol':
            angles = chain(range(-180, 0, step),
                           range(0, -180, -step))
        elif loop == 'consistent':
            angles = range(0, -180, -step)

    rec = record(obj)
    for i in angles:
        ax.camera.azimuth = i
        ax.Draw()
        fig.DrawNow()

    rec.Stop()
    rec.Export(join(img_dir, 'image.png'))

    if poster:
        ax.camera.azimuth = poster_angle
        ax.Draw()
        fig.DrawNow()
        screenshot(join(img_dir, 'poster.jpg'), obj)

    ax.camera.azimuth = AZIMUTH

    return img_dir
