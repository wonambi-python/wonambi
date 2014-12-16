"""Module to plot all the elements as lines.

"""
from logging import getLogger
lg = getLogger('phypno')

from numpy import array, max, min
from vispy.scene import SceneCanvas
from vispy.scene.visuals import Line, GridLines

from .base import Viz


ONE_CHANNEL_HEIGHT = 30


class Viz1(Viz):
    def __init__(self):
        """Class to generate lines."""
        self._canvas = SceneCanvas()
        self._viewbox = []

    def add_data(self, data, trial=0, axis_x='time', axis_subplot='chan',
                 limits_x=None, limits_y=None, grid=True):
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
        grid : bool
            with grid or not
        """
        main_grid = self._canvas.central_widget.add_grid()

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

            viewbox = main_grid.add_view(row=cnt, col=0)
            line = Line(array((x, dat)).T)
            viewbox.add(line)
            if grid:
                GridLines(parent=viewbox.scene)

            self._viewbox.append(viewbox)

        if limits_x is not None:
            min_x, max_x = limits_x

        if limits_y is not None:
            min_y, max_y = limits_y

        for viewbox in self._viewbox:
            viewbox.camera.rect = min_x, min_y, max_x - min_x, max_y - min_y

        self._canvas.size = (self._canvas.size[0],
                             ONE_CHANNEL_HEIGHT * len(subplot_values))

        self._canvas.show()
