from . import *


from phypno.utils import create_data
from phypno.viz.plot_1d import Viz1

data = create_data()


def test_viz_plot_xy():
    lg.info('---\nfunction: ' + stack()[0][3])

    v = Viz1()
    v.add_chantime(data)

    plot_xy(data)
    plot_xy(data, y_limits=(0, 10))
