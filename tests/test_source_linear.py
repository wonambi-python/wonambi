from wonambi.attr import Surf, Channels
from wonambi.source import Linear

from .paths import (surf_path,
                    chan_path,
                    )

def test_source_linear():
    surf = Surf(surf_path)
    channels = Channels(chan_path)

    Linear(surf, channels)
