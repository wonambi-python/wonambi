"""Module to plot all the elements in 3d space.

"""

from numpy import hstack, asarray
import visvis as vv


CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255.)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255.)


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
    fig = vv.figure(fig)
    ax = vv.gca()
    ax.axis.visible = False
    return fig


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

    ax = vv.gca()
    m = vv.Mesh(ax, vertices=surf.vert, faces=surf.tri)
    m.faceColor = hstack((asarray(SKIN_COLOR), .5))
    return fig


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
        s = vv.solidSphere(list(one_chan.xyz), scaling=1.5)
        s.faceColor = color
    return fig

