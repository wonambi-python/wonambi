from . import *


from phypno.utils import create_data
from phypno.viz.plot_1d import plot_xy

data = create_data()


def test_viz_plot_chan_and_surf():
    lg.info('---\nfunction: ' + stack()[0][3])

    plot_xy(data)
