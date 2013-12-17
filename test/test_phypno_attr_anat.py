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
lg.info('Missing KeyError because I cannot del environ["FREESURFER_HOME"] in '
        'import_freesurfer_LUT')
lg.info('Nibabel in Python 3 cannot read_geometry')

from numpy import array
from phypno.attr import Freesurfer, Surf
from phypno.attr.anat import import_freesurfer_LUT

fs_dir = '/home/gio/recordings/MG65/mri/proc/freesurfer'


def test_import_freesurfer_LUT_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    import_freesurfer_LUT()


def test_import_freesurfer_LUT_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    import_freesurfer_LUT('/opt/freesurfer/FreeSurferColorLUT.txt')


@raises(IOError, OSError)
def test_import_freesurfer_LUT_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    import_freesurfer_LUT('/aaa')


@raises(NotImplementedError)
def test_Surf_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    Surf(fs_dir, 'lh', 'pial')


@raises(OSError)
def test_Freesurfer_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    fs = Freesurfer('')


def test_Freesurfer_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    fs = Freesurfer(fs_dir, '/aaa')


def test_Freesurfer_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    fs = Freesurfer(fs_dir)
    assert fs.dir == fs_dir
    assert fs.lookuptable['index'][-1] == 14175
    assert fs.lookuptable['label'][-1] == 'wm_rh_S_temporal_transverse'
    assert all(fs.lookuptable['RGBA'][-1, :] == array([221., 60., 60., 0]))

    region_label, approx = fs.find_brain_region([37, 48, 16])
    assert region_label == 'ctx-rh-parsorbitalis'
    assert approx == 0

    region_label, approx = fs.find_brain_region([0, 0, 0], 2)
    assert region_label == '--not found--'
    assert approx == 2

    region_label, approx = fs.find_brain_region([0, 0, 0], 5)
    assert region_label == 'Left-VentralDC'
    assert approx == 4

    l0, l1, l2 = fs.read_label('lh')
    assert l0[-1] == 27
    assert l1.shape == (36, 5)
    assert l1[-1, -1] == 2146559
    assert l2[-1] == 'insula'

    # s0, s1 = fs.read_surf('lh')
