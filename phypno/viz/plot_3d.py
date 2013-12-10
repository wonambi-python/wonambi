"""Module to plot all the elements in 3d space.

It currently depends on mayavi, however long-term idea is to use a different
package that works with python3.

"""
from __future__ import division
from mayavi import mlab

CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255.)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255.)


def plot_surf(surf, color=SKIN_COLOR, opacity=1):
    """Plot a 3d surface, like a mesh.

    Parameters
    ----------
    surf : instance of anat.Surf
    color : tuple of 3 int
        RGB colors (between 0 and 1) of the color of the surface
    opacity : int
        opacity (the opposite of transparency), between 0 and 1

    Returns
    -------
    instance of mayavi.modules.surface.Surface

    """

    mesh = mlab.pipeline.triangular_mesh_source(surf.vert[:, 0],
                                                surf.vert[:, 1],
                                                surf.vert[:, 2],
                                                surf.tri)
    surf = mlab.pipeline.surface(mesh, color=SKIN_COLOR, opacity=opacity)

    return surf


def plot_chan(chan, color=CHAN_COLOR, scale_factor=5):
    """Plot channels in 3d space.

    Parameters
    ----------
    chan : instance of anat.Chan
    color : tuple of 3 int
        RGB colors (between 0 and 1) of the color of the electrodes
    scale_factor : int
        opacity (the opposite of transparency), between 0 and 1

    """

    for i in xrange(chan.xyz.shape[0]):
        mlab.points3d(chan.xyz[i, 0], chan.xyz[i, 1], chan.xyz[i, 2],
                      color=color, scale_factor=scale_factor)
