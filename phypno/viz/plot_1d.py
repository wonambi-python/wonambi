"""Module to plot all the elements as lines.
"""
from numpy import max, min
from vispy.plot import Fig

from .base import Viz


ONE_CHANNEL_HEIGHT = 30


class Viz1(Viz):
    def __init__(self, color='wk'):  # white on black
        """Class to generate lines.
        TODO: describe attributes
        """
        self._color = color

        self._fig = Fig()

        self._limits_x = None  # tuple
        self._limits_y = None  # tuple

    def add_data(self, data, trial=0, axis_x='time', axis_subplot='chan',
                 limits_x=None, limits_y=None, color=None):
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
        if color is None:
            color = self._color[0]

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

            self._fig[cnt, 0].plot((x, dat), color=color)

        if limits_x is not None:
            min_x, max_x = limits_x
        for onewidget in self._fig.plot_widgets:
            onewidget.view.camera.set_range(x=(min_x, max_x))

        if limits_y is not None:
            min_y, max_y = limits_y
        for onewidget in self._fig.plot_widgets:
            onewidget.view.camera.set_range(y=(min_y, max_y))

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
                # TODO: 2 * is arbitrary
                up = p.plot((start_time, end_time), (3 * peak_val, 3 * peak_val),
                            pen=color)
                down = p.plot((start_time, end_time),
                              (-3 * peak_val, -3 * peak_val), pen=color)
                filled = FillBetweenItem(up, down, brush=color)
                self._plots[chan].addItem(filled)
