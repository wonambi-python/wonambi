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


def test_plot3d_surf_chan():

    surf = Surf(surf_path)
    channels = Channels(chan_path)

    v = Viz3()
    v.add_chan(channels)
    v.add_surf(surf, alpha=.8)

    v.save(VIZ_PATH / 'viz3_02_surf_chan.png')
