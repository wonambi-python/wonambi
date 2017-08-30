from wonambi.attr import Channels
from wonambi.attr.chan import find_channel_groups

from .paths import (chan_path,
                    exported_chan_path,
                    )


def test_channels():
    chan = Channels(chan_path)
    assert chan.n_chan == 28

    xyz = chan.return_xyz()
    assert xyz.shape == (28, 3)

    labels = chan.return_label()
    assert len(labels) == 28


def test_channels_grid():
    chan = Channels(chan_path)

    grid_chan = chan(lambda x: x.label.startswith('grid'))
    assert grid_chan.n_chan == 16

    grid_chan.export(exported_chan_path)

    imported = Channels(exported_chan_path)
    assert imported.n_chan == grid_chan.n_chan


def test_channel_groups():
    chan = Channels(chan_path)
    groups = find_channel_groups(chan)
    assert len(groups) == 3
