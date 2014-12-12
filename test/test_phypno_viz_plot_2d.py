from . import *

from numpy import arange
from numpy.random import seed

from phypno.attr import Channels
from phypno.utils import create_data
from phypno.viz.plot_2d import Viz2

elec_file = join(data_dir, 'MGXX/doc/elec/elec_pos_adjusted.csv')
chan = Channels(elec_file)

seed(2014)
data = create_data()


def test_viz_plot2d_data_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz2()
    v.add_data(data)
    assert v._repr_png_()[2000:2010] == b'@\x00\x04@\x00\x04@\x00\x04@'


def test_viz_plot2d_data_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz2()
    v.add_data(data, limits_c=(-1, 1))
    assert v._repr_png_()[2000:2010] == b';\xafu\x0c\x00\xc9\x00\x08\x80\x00'


def test_viz_plot2d_topo_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz2()
    v.add_topo(chan, arange(chan.n_chan))
    assert v._repr_png_()[2000:2010] == b'\x19\x9d\x00\xe1\x9c\x90\xb5\x81\xa4\xf5'


def test_viz_plot2d_topo_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz2()
    v.add_topo(chan, arange(chan.n_chan), limits_c=(-1, 1))
    assert v._repr_png_()[2000:2010] == b'\xece\x82\xc2\xcb\\\x1e\x7f\xa8\x0f'
