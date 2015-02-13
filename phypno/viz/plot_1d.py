"""Module to plot all the elements as lines.

"""
from numpy import max, min
from pyqtgraph import GraphicsLayoutWidget

from .base import Viz


ONE_CHANNEL_HEIGHT = 30


class Viz1(Viz):
    def __init__(self):
        """Class to generate lines."""
        self._widget = GraphicsLayoutWidget()
        self._plots = []

    def add_data(self, data, trial=0, axis_x='time', axis_subplot='chan',
                 limits_x=None, limits_y=None):
        """
        Parameters
        ----------
        data : any instance of DataType
            Duck-typing should help
        trial : int
            index of the trial to plot
        axis_x : str, optional
            value to plot on x-axis, such as 'time' or 'freq'
        axis_subplot : str, optional
            axis to use for subplot
        limits_x : tuple, optional
            limits on the x-axis (if unspecified, it's the max across subplots)
        limits_y : tuple, optional
            limits on the y-axis (if unspecified, it's the max across subplots)
        """
        x = data.axis[axis_x][trial]
        max_x = max(x)
        min_x = min(x)

        subplot_values = data.axis[axis_subplot][trial]

        max_y = 0
        min_y = 0

        self._plots = []
        for cnt, one_value in enumerate(subplot_values):
            selected_axis = {axis_subplot: one_value}
            dat = data(trial=trial, **selected_axis)

            max_y = max((max_y, max(dat)))
            min_y = min((min_y, min(dat)))

            p = self._widget.addPlot(title=one_value)
            if (cnt + 1) < len(subplot_values):
                p.hideAxis('bottom')
            p.plot(x, dat)
            self._widget.nextRow()
            self._plots.append(p)

        if limits_x is not None:
            min_x, max_x = limits_x
            for one_plot in self._plots:
                one_plot.setXRange(min_x, max_x)

        if limits_y is not None:
            min_y, max_y = limits_y
            for one_plot in self._plots:
                one_plot.setYRange(min_y, max_y)

        self._widget.show()
