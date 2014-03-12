from inspect import stack
from logging import getLogger
from nose.tools import raises
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

data_dir = '/home/gio/tools/phypno/data'

#-----------------------------------------------------------------------------#

from os.path import join

from phypno.attr import Freesurfer, Channels
from phypno.viz.plot_3d import plot_surf, plot_chan

fs_dir = join(data_dir, 'MGXX/mri/proc/freesurfer')
chan_file = join(data_dir, 'MGXX/doc/elec/elec_pos_adjusted.csv')

anat = Freesurfer(fs_dir)
chan = Channels(chan_file)
hemi = 'lh'


def test_viz_plot_3d_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    neuroport = chan(lambda x: x.label.lower() == 'neuroport')
    other_chan = chan(lambda x: not x.label.lower() == 'neuroport')

    fig = plot_chan(neuroport, color=(0, 1, 0, 1))
    plot_chan(other_chan, fig, color=(1, 0, 0, 1))

    surf = anat.read_surf(hemi)
    plot_surf(surf, fig)

