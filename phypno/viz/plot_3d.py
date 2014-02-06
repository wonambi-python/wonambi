"""Module to plot all the elements in 3d space.

"""

from numpy import hstack, asarray
import visvis as vv

vv.figure()
ax = vv.gca()
ax.axis.visible = False

CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255.)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255.)


def plot_surf(surf):
    m = vv.Mesh(ax, vertices=surf.vert, faces=surf.tri)
    m.faceColor = hstack((asarray(SKIN_COLOR), .5))


def plot_chan(chan):
    for i in range(chan.n_chan()):
        s = vv.solidSphere(list(chan.xyz[i, :]), scaling=2)
        s.faceColor = (0, 0, 0, 1)

