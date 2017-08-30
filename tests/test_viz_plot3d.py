from wonambi.viz import Viz3
from wonambi.attr import Surf, Channels

from .paths import (surf_path,
                    chan_path,
                    VIZ_PATH,
                    )


def test_widget_labels(qtbot):

    surf = Surf(surf_path)

    v = Viz3()
    v.add_surf(surf)
    v.save(VIZ_PATH / 'viz3_01_surf.png')

    channels = Channels(chan_path)
