"""Module to plot all the elements as flat images.
"""
from numpy import nanmax, nanmin

from .base import Viz


class Viz2(Viz):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def add_data(self, data, trial=0, limits_c=None):
        """
        Parameters
        ----------
        data : any instance of DataType
            Duck-typing should help
        trial : int
            index of the trial to plot
        limits_c : tuple, optional
            limits on the z-axis (if unspecified, it's the max across subplots)
        """
        dat = data(trial=trial)

        if limits_c is None:
            max_c = nanmax(dat)
            min_c = nanmin(dat)
        else:
            min_c, max_c = limits_c

        for cnt in range(1):
            self._fig[cnt, 0].plot(dat, clim=(min_c, max_c))
