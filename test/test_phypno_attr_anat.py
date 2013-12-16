from inspect import stack
from logging import getLogger, FileHandler, DEBUG
from os.path import join, basename, splitext
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
from numpy import array
from phypno.attr import Freesurfer
from phypno.attr.anat import import_freesurfer_LUT

fs_dir = '/home/gio/recordings/MG65/mri/proc/freesurfer'


def test_01_import_freesurfer_LUT():
    lg.info('---\nfunction: ' + stack()[0][3])
    import_freesurfer_LUT()


def test_02_import_freesurfer_LUT():
    lg.info('---\nfunction: ' + stack()[0][3])
    import_freesurfer_LUT('/opt/freesurfer/FreeSurferColorLUT.txt')


def test_03_Freesurfer():
    lg.info('---\nfunction: ' + stack()[0][3])
    fs = Freesurfer(fs_dir)
    assert fs.dir == fs_dir
    assert fs.lookuptable['index'][-1] == 14175
    assert fs.lookuptable['label'][-1] == 'wm_rh_S_temporal_transverse'
    assert all(fs.lookuptable['RGBA'][-1, :] == array([221., 60., 60., 0]))
    region_label, approx = fs.find_brain_region([37, 48, 16])
    assert region_label == 'ctx-rh-parsorbitalis'
    assert approx == 0
    region_label, approx = fs.find_brain_region([0, 0, 0], 5)
    assert region_label == 'Left-VentralDC'
    assert approx == 4

