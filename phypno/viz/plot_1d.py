"""Module to plot all the elements as lines.
"""
from numpy import nanmax, nanmin
from vispy.scene.visuals import Rectangle

from .base import Viz


ONE_CHANNEL_HEIGHT = 30


class Viz1(Viz):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._limits_x = None  # tuple
        self._limits_y = None  # tuple

    def add_data(self, data, trial=0, axis_x='time', axis_subplot='chan',
                 limits_x=None, limits_y=None, color='k'):
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
        max_x = nanmax(x)
        min_x = nanmin(x)

        subplot_values = data.axis[axis_subplot][trial]

        max_y = 0
        min_y = 0

        for cnt, one_value in enumerate(subplot_values):
            selected_axis = {axis_subplot: one_value}
            dat = data(trial=trial, **selected_axis)

            max_y = nanmax((max_y, nanmax(dat)))
            min_y = nanmin((min_y, nanmin(dat)))

            plt = self._fig[cnt, 0]
            plt.name = one_value
            plt.plot((x, dat), color=color, ylabel=one_value)

        if limits_x is not None:
            min_x, max_x = limits_x
        if limits_y is not None:
            min_y, max_y = limits_y
        for plt in self._fig.plot_widgets:
            plt.view.camera.set_range(x=(min_x, max_x), y=(min_y, max_y))

        self._limits_x = min_x, max_x
        self._limits_y = min_y, max_y

    def add_graphoelement(self, graphoelement, color='r', height=100):
        """Add graphoelements (at the moment, only spindles, but it works fine)

        Parameters
        ----------
        graphoelement : instance of Spindles
            the detected spindles
        color : str or 3-, 4- tuple
            color to use for the area of detection.
        height : float
            height of the highlight area

        Todo
        ----
            testing todo
        """
        for one_sp in graphoelement:
            chan = one_sp['chan']  # it could be over multiple channels
            start_time = one_sp['start_time']
            end_time = one_sp['end_time']

            if end_time > self._limits_x[0] and start_time < self._limits_x[1]:
                if start_time < self._limits_x[0]:
                    start_time = self._limits_x[0]
                if end_time > self._limits_x[1]:
                    end_time = self._limits_x[1]

                for plt in self._fig.plot_widgets:
                    if plt.name and plt.name in chan:
                        time_center = (end_time + start_time) / 2
                        width = end_time - time_center
                        rect = Rectangle(center=(time_center, 0), color=color,
                                         height=height, width=width)
                        rect.order = -1
                        plt.view.add(rect)
