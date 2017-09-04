from wonambi.viz import Viz3
from wonambi.attr import Surf, Channels

from .paths import (surf_path,
                    chan_path,
                    VIZ_PATH,
                    )


def test_plot3d_surf():

    surf = Surf(surf_path)

    v = Viz3()
    v.add_surf(surf)

    v.save(VIZ_PATH / 'viz3_01_surf.png')
    v.close()


def test_plot3d_surf_color():

    surf = Surf(surf_path)

    v = Viz3()
    v.add_surf(surf, color=(.5, .5, 0))

    v.save(VIZ_PATH / 'viz3_02_surf_color.png')
    v.close()


def test_plot3d_surf_value():

    surf = Surf(surf_path)

    v = Viz3()
    v.add_surf(surf, values=surf.vert[:, 2], limits_c=(0, 50))

    v.save(VIZ_PATH / 'viz3_03_surf_values.png')
    v.close()


def test_plot3d_surf_chan():

    surf = Surf(surf_path)
    channels = Channels(chan_path)

    v = Viz3()
    v.add_chan(channels)
    v.add_surf(surf, alpha=.8)

    v.save(VIZ_PATH / 'viz3_04_surf_chan.png')
    v.close()


def test_plot3d_surf_chan_color_one():

    surf = Surf(surf_path)
    channels = Channels(chan_path)

    v = Viz3()
    v.add_chan(channels, color=(1, 0, 0))
    v.add_surf(surf, alpha=.5)

    v.save(VIZ_PATH / 'viz3_05_surf_chan_color_one.png')
    v.close()


def test_plot3d_surf_chan_color_one_alpha():

    surf = Surf(surf_path)
    channels = Channels(chan_path)

    v = Viz3()
    v.add_chan(channels, color=(1, 0, 0), alpha=0.5)
    v.add_surf(surf, alpha=.5)

    v.save(VIZ_PATH / 'viz3_06_surf_chan_color_one_alpha.png')
    v.close()


def test_plot3d_surf_chan_color_everyother():

    from numpy import tile

    surf = Surf(surf_path)
    channels = Channels(chan_path)

    color_everyother = tile([[1, 0, 0], [0, 0, 1]], (14, 1))

    v = Viz3()
    v.add_chan(channels, color=color_everyother)
    v.add_surf(surf, alpha=.5)

    v.save(VIZ_PATH / 'viz3_07_surf_chan_color_everyother.png')
    v.close()


def test_plot3d_surf_chan_values():

    from numpy import arange

    surf = Surf(surf_path)
    channels = Channels(chan_path)

    v = Viz3()
    v.add_chan(channels, values=arange(channels.n_chan))
    v.add_surf(surf, alpha=.5)

    v.save(VIZ_PATH / 'viz3_08_surf_chan_values.png')
    v.close()

    # reuse the limits_c
    v.add_chan(channels, values=arange(channels.n_chan))
