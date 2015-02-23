"""Module to plot all the elements as lines.

"""
from numpy import max, min
from pyqtgraph import GraphicsLayoutWidget, FillBetweenItem

from .base import Viz


ONE_CHANNEL_HEIGHT = 30


class Viz1(Viz):
    def __init__(self):
        """Class to generate lines.
        TODO: describe attributes
        """
        self._widget = GraphicsLayoutWidget()
        self._plots = {}

        self._limits_x = None  # tuple
        self._limits_y = None  # tuple

    def add_data(self, data, trial=0, axis_x='time', axis_subplot='chan',
                 limits_x=None, limits_y=None, color='w'):
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

        for cnt, one_value in enumerate(subplot_values):
            selected_axis = {axis_subplot: one_value}
            dat = data(trial=trial, **selected_axis)

            max_y = max((max_y, max(dat)))
            min_y = min((min_y, min(dat)))

            if one_value in self._plots:
                p = self._plots[one_value]
            else:
                p = self._widget.addPlot(title=one_value)
                self._plots[one_value] = p
                self._widget.nextRow()

            if (cnt + 1) < len(subplot_values):
                p.hideAxis('bottom')
            p.plot(x, dat, pen=color)

        if limits_x is not None:
            min_x, max_x = limits_x
            for one_plot in self._plots.values():
                one_plot.setXRange(min_x, max_x)

        if limits_y is not None:
            min_y, max_y = limits_y
            for one_plot in self._plots.values():
                one_plot.setYRange(min_y, max_y)

        self._widget.show()
        self._limits_x = min_x, max_x
        self._limits_y = min_y, max_y

    def add_graphoelement(self, graphoelement, color='r'):
        """Add graphoelements (at the moment, only spindles, but it works fine)

        Parameters
        ----------
        graphoelement : instance of Spindles
            the detected spindles
        color : str
            color to use for the area of detection.
        """
        for one_sp in graphoelement:
            chan = one_sp['chan']  # it could be over multiple channels
            start_time = one_sp['start_time']
            end_time = one_sp['end_time']
            peak_val = one_sp['peak_val']

            if chan in self._plots and end_time > self._limits_x[0] and start_time < self._limits_x[1]:
                if start_time < self._limits_x[0]:
                    start_time = self._limits_x[0]
                if end_time > self._limits_x[1]:
                    end_time = self._limits_x[1]

                p = self._plots[chan]
                up = p.plot((start_time, end_time), (peak_val, peak_val),
                            pen=color)
                down = p.plot((start_time, end_time),
                              (-1 * peak_val, -1 * peak_val), pen=color)
                filled = FillBetweenItem(up, down, brush=color)
                print('a')
                self._plots[chan].addItem(filled)
