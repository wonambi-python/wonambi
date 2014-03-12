"""Module to plot all the elements in 3d space.

"""

from numpy import hstack, asarray
import visvis as vv


CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255.)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255.)


def _make_fig(fig=None):
    fig = vv.figure(fig)
    ax = vv.gca()
    ax.axis.visible = False
    return fig


def plot_surf(surf, fig=None):
    fig = _make_fig(fig)

    ax = vv.gca()
    m = vv.Mesh(ax, vertices=surf.vert, faces=surf.tri)
    m.faceColor = hstack((asarray(SKIN_COLOR), .5))
    return fig


def plot_chan(chan, fig=None, color=(0, 0, 0, 1)):
    fig = _make_fig(fig)

    for one_chan in chan.chan:
        s = vv.solidSphere(list(one_chan.xyz), scaling=1.5)
        s.faceColor = color
    return fig

