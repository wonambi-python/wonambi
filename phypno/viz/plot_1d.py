"""Module to plot all the elements in 3d space.

"""
from logging import getLogger
lg = getLogger('phypno')

from visvis import figure, subplot, gca, plot

FIGURE_SIZE = (1280, 720)
BOTTOM_ROW = 144


def plot_xy(data, axis_x='time', axis_subplot='chan'):
    """Plot recordings, so that you can scroll through it.

    Parameters
    ----------
    data : any instance of DataType
        Duck-typing should help
    axis_x : str, optional
        value to plot on x-axis, such as 'time' or 'freq'
    axis_subplot : str, optional
        axis to use for subplot


    """
    fig = _make_fig()  # always make new figure
    fig.Clear()  # necessary, otherwise, subplot raises the existing axis

    trial = 0

    x = data.axis[axis_x][trial]
    subplot_values = data.axis[axis_subplot][trial]

    for cnt, one_value in enumerate(subplot_values):
        selected_axis = {axis_subplot: one_value}
        d = data(trial=trial, **selected_axis)
        if d.shape != x.shape:
            raise ValueError('The shape of the data (' + str(d.shape) + ') is '
                             'different from the shape of x (' + str(x.shape)
                             + ')')
        subplot(len(subplot_values), 1, cnt + 1)
        plot(x, d)



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