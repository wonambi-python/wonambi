from os import environ
from numpy import array
from numpy.testing import assert_array_equal
from pytest import approx, raises

from wonambi.attr import Freesurfer, Surf
from wonambi.attr.anat import import_freesurfer_LUT

from .paths import (FREESURFER_HOME,
                    LUT_path,
                    fs_path,
                    surf_path,
                    )

environ['FREESURFER_HOME'] = str(FREESURFER_HOME)


def test_import_freesurfer_LUT_01():
    idx, label, rgba = import_freesurfer_LUT()
    assert idx[-1] == 14175
    assert label[-1] == 'wm_rh_S_temporal_transverse'
    assert_array_equal(rgba[-1, :], array([221., 60., 60., 0.]))


def test_import_freesurfer_LUT_02():
    del environ['FREESURFER_HOME']
    with raises(OSError):
        import_freesurfer_LUT()


def test_import_freesurfer_LUT_03():
    import_freesurfer_LUT(LUT_path)


def test_import_freesurfer_LUT_04():
    import_freesurfer_LUT(str(LUT_path))


def test_import_freesurfer_LUT_05():
    with raises(FileNotFoundError):
        import_freesurfer_LUT(FREESURFER_HOME / 'does_not_exist')


def test_Surf_01():
    Surf(surf_path)


def test_Surf_02():
    Surf(str(surf_path))


def test_Freesurfer_01():
    with raises(OSError):
        Freesurfer('does_not_exist')


fs = Freesurfer(fs_path)

def test_Freesurfer_02():
    fs.read_brain()

def test_Freesurfer_03():
    assert fs.dir == fs_path
    assert fs.lookuptable['index'][-1] == 14175
    assert fs.lookuptable['label'][-1] == 'wm_rh_S_temporal_transverse'
    assert_array_equal(fs.lookuptable['RGBA'][-1, :],
                       array([221., 60., 60., 0.]))


def test_Freesurfer_04():
    region_label, approx = fs.find_brain_region([37, 48, 16])
    assert region_label == 'ctx-rh-rostralmiddlefrontal'
    assert approx == 0


def test_Freesurfer_05():
    region_label, approx = fs.find_brain_region([10, 0, 0], max_approx=2)
    assert region_label == 'Right-Cerebral-White-Matter'
    assert approx == 0


def test_Freesurfer_06():
    l0, l1, l2 = fs.read_label('lh')
    assert l0[-1] == 14
    assert l1.shape == (36, 5)
    assert l1[-1, -1] == 2146559
    assert l2[-1] == 'insula'


def test_Freesurfer_shift():
    approx(fs.surface_ras_shift) == array([5.39971924, 18., 0.])
