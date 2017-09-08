from nibabel import load as nload
from wonambi.attr import Channels, Freesurfer
from wonambi.attr.chan import (find_channel_groups,
                               create_sphere_around_elec,
                               )

from .paths import (chan_path,
                    fs_path,
                    template_mri_path,
                    exported_chan_path,
                    )

chan = Channels(chan_path)

def test_channels():
    assert chan.n_chan == 28

    xyz = chan.return_xyz()
    assert xyz.shape == (28, 3)

    labels = chan.return_label()
    assert len(labels) == 28


def test_channels_grid():
    grid_chan = chan(lambda x: x.label.startswith('grid'))
    assert grid_chan.n_chan == 16

    grid_chan.export(exported_chan_path)

    imported = Channels(exported_chan_path)
    assert imported.n_chan == grid_chan.n_chan


def test_channel_groups():
    groups = find_channel_groups(chan)
    assert len(groups) == 3


def test_channel_sphere():
    xyz = chan.return_xyz()[0,:]
    fs = Freesurfer(fs_path)
    mask = create_sphere_around_elec(xyz, template_mri_path,
                                     distance=8,
                                     freesurfer=fs)
    assert mask.sum() == 4

    template_mri = nload(str(template_mri_path))

    xyz_volume = xyz + fs.surface_ras_shift
    mask = create_sphere_around_elec(xyz, template_mri, distance=16)
    assert mask.sum() == 35
