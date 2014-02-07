from inspect import stack
from logging import getLogger
from nose.tools import raises
from numpy.testing import assert_array_equal
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

#-----------------------------------------------------------------------------#
from os.path import join
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
    assert_array_equal(ch.return_chan_xyz(['FPS1']),
                       array([[-17. ,  68. ,  20.5]]))
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
    assert ch.assign_region(fs, ['LAF1'],
                            1) == ['ctx-rh-caudalanteriorcingulate']


def test_find_chan_in_region_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Chan(elec_file)
    fs = Freesurfer(fs_dir)
    assert ch.find_chan_in_region(fs, 'cingulate') == ['LOF1', 'LOF2', 'LAF1',
                                                       'LAF2', 'LMF2']
