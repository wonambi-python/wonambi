from . import *

from numpy.random import seed

from phypno.utils import create_data
from phypno.viz.plot_1d import Viz1

seed(2014)
data = create_data()


def test_viz_plot1d_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz1()
    v.add_data(data, limits_x=(0, 1), limits_y=(-3, 3))
    assert v._repr_png_()[2000:2010] == b'\xc7uU\x80D\xfe\x1cl\xb2\xfd'

