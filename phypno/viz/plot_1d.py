"""Module to plot all the elements in 3d space.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import max, min
from visvis import figure, subplot, gca, plot


FIGURE_SIZE = (1280, 720)
BOTTOM_ROW = 144


def plot_xy(data, axis_x='time', axis_subplot='chan',
            y_limits=None):
    """Plot recordings, so that you can scroll through it.

    Parameters
    ----------
    data : any instance of DataType
        Duck-typing should help
    axis_x : str, optional
        value to plot on x-axis, such as 'time' or 'freq'
    axis_subplot : str, optional
        axis to use for subplot
    y_limits : tuple, optional
        limits on the y-axis (if unspecified, it's the max across subplots)

    Returns
    -------
    instance of visvis.Figure

    """
    fig = _make_fig()  # always make new figure
    fig.Clear()  # necessary, otherwise, subplot raises the existing axis

    trial = 0

    x = data.axis[axis_x][trial]
    subplot_values = data.axis[axis_subplot][trial]

    y_max = 0
    y_min = 0

    for cnt, one_value in enumerate(subplot_values):
        selected_axis = {axis_subplot: one_value}
        dat = data(trial=trial, **selected_axis)
        y_max = max((y_max, max(dat)))
        y_min = min((y_min, min(dat)))

        if dat.shape != x.shape:
            raise ValueError('The shape of the data (' + str(dat.shape) + ') '
                             'is different from the shape of x (' +
                             str(x.shape) + ')')
        subplot(len(subplot_values), 1, cnt + 1)
        plot(x, dat)

    if y_limits is None:
        y_minmax = (y_min, y_max)
    else:
        y_minmax = y_limits

    for cnt in range(len(subplot_values)):
        ax = subplot(len(subplot_values), 1, cnt + 1)
        ax.SetLimits(rangeY=y_minmax)

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
