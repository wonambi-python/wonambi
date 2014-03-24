"""Module to plot all the elements in 3d space.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import hstack, asarray, dot, zeros
from numpy.linalg import norm
from visvis import Mesh, gca, figure, solidSphere, CM_JET


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

    """
    fig = _make_fig(fig)

    ax = gca()
    m = Mesh(ax, vertices=surf.vert, faces=surf.tri)
    m.faceColor = hstack((asarray(SKIN_COLOR), 0.5))

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

    ax = gca()
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
        dist_func = lambda one_vert, one_chan : 1 / norm(one_vert - one_chan)

    trans = zeros((surf.vert.shape[0], xyz.shape[0]))

    for i, one_vert in enumerate(surf.vert):
        for j, one_xyz in enumerate(xyz):
            trans[i, j] = dist_func(one_vert, one_xyz)

    return trans


def plot_chan(chan, fig=None, color=(0, 0, 0, 1)):
    """Plot channels in 3d space.

    Parameters
    ----------
    chan : instance of phypno.attr.Channels
        channels to plot.
    fig : instance of visvis.Figure, optional
        figure being plotted.
    color : tuple
        4-element tuple, representing RGB and alpha.

    Returns
    -------
    instance of visvis.Figure

    """
    fig = _make_fig(fig)

    for one_chan in chan.chan:
        s = solidSphere(list(one_chan.xyz), scaling=1.5)
        s.faceColor = color

    return fig


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
