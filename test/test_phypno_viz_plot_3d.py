from . import *

from numpy import ones

from phypno.attr import Freesurfer
from phypno.viz.plot_3d import Viz3

filename = '/home/gio/recordings/MG72/mri/proc/freesurfer'
fs = Freesurfer(filename)
surf = fs.read_surf('lh')
from phypno.attr import Channels
chan = Channels('/home/gio/recordings/MG72/doc/elec/MG72_elec_pos-names_sessA.csv')


def test_viz_plot3d_surf_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz3()
    v.add_surf(surf, values=surf.vert[:, 1])
    assert v._repr_png_()[2000:2010] == b'\x0f@DDDDD\xda\xa1\xfa'


def test_viz_plot3d_surf_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz3()
    v.add_surf(surf, values=surf.vert[:, 1], limits_c=(-10, 10))
    assert v._repr_png_()[2000:2010] == b'\xf1\xc67\x8d\x002\xa9\x1e\xc3\x1a'


def test_viz_plot3d_surf_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz3()
    v.add_surf(surf, values=surf.vert[:, 1], limits_c=(-10, 10))
    v.update_surf(values=surf.vert[:, 0])
    assert v._repr_png_()[2000:2010] == b'\x10\x11\x11\x11\x11\x11\xefp\xbd\x00'


def test_viz_plot3d_chan_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz3()
    v.add_chan(chan, values=chan.return_xyz()[:, 0], limits_c=(-50, 0))
    lg.info(v._repr_png_()[2000:2010])
    # assert v._repr_png_()[2000:2010] is everytime different


def test_viz_plot3d_chan_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz3()
    v.add_surf(surf, color=(.5, .5, .5, .1))
    v.add_chan(chan)
    # assert v._repr_png_()[2000:2010] is everytime different
