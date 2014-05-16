from . import *

lg.info('Missing KeyError because I cannot del environ["FREESURFER_HOME"] in '
        'import_freesurfer_LUT')

from os import environ
from os.path import join
from numpy import array
from phypno.attr import Freesurfer, Surf
from phypno.attr.anat import import_freesurfer_LUT

fs_dir = join(data_dir, 'MGXX/mri/proc/freesurfer')
FREESURFER_HOME = environ['FREESURFER_HOME']


def test_import_freesurfer_LUT_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    import_freesurfer_LUT()


@raises(OSError)
def test_import_freesurfer_LUT_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    del environ['FREESURFER_HOME']
    import_freesurfer_LUT()


def test_import_freesurfer_LUT_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    import_freesurfer_LUT(join(FREESURFER_HOME, 'FreeSurferColorLUT.txt'))


@raises(FileNotFoundError)
def test_import_freesurfer_LUT_04():
    lg.info('---\nfunction: ' + stack()[0][3])

    import_freesurfer_LUT(join(data_dir, 'does_not_exist'))


def test_Surf_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    Surf(fs_dir, 'lh', 'pial')


def test_Surf_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    Surf(join(fs_dir, 'surf', 'lh' + '.' + 'pial'))


@raises(OSError)
def test_Freesurfer_01():
    lg.info('---\nfunction: ' + stack()[0][3])

    Freesurfer('')


def test_Freesurfer_02():
    lg.info('---\nfunction: ' + stack()[0][3])

    Freesurfer(fs_dir, join(data_dir, 'does_not_exist'))


fs = Freesurfer(fs_dir)


def test_Freesurfer_03():
    lg.info('---\nfunction: ' + stack()[0][3])

    assert fs.dir == fs_dir
    assert fs.lookuptable['index'][-1] == 14175
    assert fs.lookuptable['label'][-1] == 'wm_rh_S_temporal_transverse'
    assert all(fs.lookuptable['RGBA'][-1, :] == array([221., 60., 60., 0]))


def test_Freesurfer_04():
    lg.info('---\nfunction: ' + stack()[0][3])

    region_label, approx = fs.find_brain_region([37, 48, 16])
    assert region_label == 'ctx-rh-parsorbitalis'
    assert approx == 0


def test_Freesurfer_05():
    lg.info('---\nfunction: ' + stack()[0][3])

    region_label, approx = fs.find_brain_region([0, 0, 0], 2)
    assert region_label == '--not found--'
    assert approx == 2


def test_Freesurfer_06():
    lg.info('---\nfunction: ' + stack()[0][3])

    region_label, approx = fs.find_brain_region([0, 0, 0], 5)
    assert region_label == 'Left-VentralDC'
    assert approx == 4


def test_Freesurfer_07():
    lg.info('---\nfunction: ' + stack()[0][3])

    l0, l1, l2 = fs.read_label('lh')
    assert l0[-1] == 27
    assert l1.shape == (36, 5)
    assert l1[-1, -1] == 2146559
    assert l2[-1] == 'insula'


def test_Freesurfer_08():
    lg.info('---\nfunction: ' + stack()[0][3])

    surf = fs.read_surf('lh')
    assert isinstance(surf, Surf)
