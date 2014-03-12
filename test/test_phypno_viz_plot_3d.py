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



#-----------------------------------------------------------------------------#


def tesaat():
    grid_strip_chan = hemi_chan(is_grid)
    neuroport = hemi_chan(lambda x: x.label.lower() == 'neuroport')
    depth_chan = hemi_chan(lambda x: not is_grid(x))

    fig = plot_chan(neuroport, color=(0, 1, 0, 1))
    plot_chan(grid_strip_chan, fig, color=(1, 0, 0, 1))
    plot_chan(depth_chan, fig, color=(0, 0, 1, 1))

