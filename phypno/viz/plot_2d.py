"""Module to plot all the elements as flat images.
"""
from numpy import nanmax, nanmin

from .base import COLORMAP, Viz


class Viz2(Viz):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def add_data(self, data, trial=0, limits_c=None, colormap=COLORMAP,
                 **kwargs):
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
        kwargs.update({'trial': trial})

        dat = data(**kwargs)

        if limits_c is None:
            max_c = nanmax(dat)
            min_c = nanmin(dat)
        else:
            min_c, max_c = limits_c

        print(min_c)
        print(max_c)

        plt = self._fig[0, 0]
        plt.image(dat.T, clim=(min_c, max_c), cmap=colormap)
        plt.view.camera.aspect = None
        plt.xaxis.axis.domain = (data.axis['time'][trial][0],
                                 data.axis['time'][trial][-1])
        self._plt = plt
