from . import *

from os.path import join
from numpy import ones

from phypno.attr import Freesurfer, Channels
from phypno.viz.plot_3d import (plot_surf, plot_chan, plot_values_on_surf,
                                calculate_chan2surf_trans)

fs_dir = join(data_dir, 'MGXX/mri/proc/freesurfer')
chan_file = join(data_dir, 'MGXX/doc/elec/elec_pos_adjusted.csv')

anat = Freesurfer(fs_dir)
chan = Channels(chan_file)
hemi = 'lh'
surf = anat.read_surf(hemi)


def test_viz_plot_chan_and_surf():
    lg.info('---\nfunction: ' + stack()[0][3])

    neuroport = chan(lambda x: x.label.lower() == 'neuroport')
    other_chan = chan(lambda x: not x.label.lower() == 'neuroport')

    fig = plot_chan(neuroport, color=(0, 1, 0, 1))
    plot_chan(other_chan, fig, color=(1, 0, 0, 1))

    plot_surf(surf, fig)


def test_viz_plot_values_on_surf():
    lg.info('---\nfunction: ' + stack()[0][3])

    trans = calculate_chan2surf_trans(surf, chan.return_xyz())
    plot_values_on_surf(surf, 5 * ones(trans.shape[1]), trans)
