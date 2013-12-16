from inspect import stack
from logging import getLogger, FileHandler, DEBUG
from os.path import join, basename, splitext
from nose.tools import raises
from subprocess import check_output
from sys import version_info


git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()

log_dir = '/home/gio/tools/phypno/test/log'
log_file = join(log_dir, splitext(basename(__file__))[0] + '_v' +
                str(version_info[0]) + '.log')
lg = getLogger('phypno')
lg.setLevel(DEBUG)
h_lg = FileHandler(log_file, mode='w')
lg.addHandler(h_lg)
lg.info('phypno ver: ' + git_ver)

#-----------------------------------------------------------------------------#
lg.info('Module: ' + __name__)

#-----------------------------------------------------------------------------#
from numpy import array
from numpy.random import random
from tempfile import mkdtemp

from phypno.attr import Chan, Freesurfer
from phypno.attr.chan import detect_format
from phypno.utils.exceptions import UnrecognizedFormat

temp_dir = mkdtemp()
fs_dir = '/home/gio/recordings/MG65/mri/proc/freesurfer'
elec_file = '/home/gio/recordings/MG65/doc/elec_pos.csv'
random_file = '/home/gio/recordings/MG65/doc/xltek_datasets'


def test_detect_format_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    assert detect_format(elec_file) == 'csv'


def test_detect_format_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    assert detect_format(random_file) == 'unknown'


@raises(UnrecognizedFormat)
def test_Chan_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Chan(random_file)


def test_Chan_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Chan(elec_file)
    assert ch.n_chan() == 103
    assert all(ch.return_chan_xyz('FPS1') == array([-17. ,  68. ,  20.5]))
    ch.export(join(temp_dir, 'elec_file.csv'))


@raises(ArithmeticError)
def test_Chan_03():
    chan_name = ['ch{0:03}'.format(x) for x in range(10)]
    xyz = random((10, 4))
    ch = Chan(chan_name, xyz)


def test_Chan_04():
    chan_name = ['ch{0:03}'.format(x) for x in range(10)]
    xyz = random((10, 3))
    ch = Chan(chan_name, xyz)


def test_assign_region_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Chan(elec_file)
    fs = Freesurfer(fs_dir)
    assert ch.assign_region(fs, 'LAF1', 1) == 'ctx-rh-caudalanteriorcingulate'



