from os import environ
from numpy import array
from numpy.testing import assert_array_equal
from pytest import raises

from phypno.attr import Freesurfer, Surf
from phypno.attr.anat import import_freesurfer_LUT

from .utils import (SAMPLE_PATH,
                    FREESURFER_HOME,
                    )

LUT_path = FREESURFER_HOME / 'FreeSurferColorLUT.txt'
fs_path =  SAMPLE_PATH / 'SUBJECTS_DIR' / 'bert'
surf_path = fs_path / 'surf' / 'lh.pial'

environ['FREESURFER_HOME'] = str(FREESURFER_HOME)


def test_import_freesurfer_LUT_01():
    idx, label, rgba = import_freesurfer_LUT()
    assert  idx[-1] == 14175
    assert label[-1] == 'wm_rh_S_temporal_transverse'
    assert_array_equal(rgba[-1], array([ 221.,   60.,   60.,    0.]))


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
        Freesurfer('')


"""

fs = Freesurfer(fs_dir)


def test_Freesurfer_03():
    assert fs.dir == fs_dir
    assert fs.lookuptable['index'][-1] == 14175
    assert fs.lookuptable['label'][-1] == 'wm_rh_S_temporal_transverse'
    assert all(fs.lookuptable['RGBA'][-1, :] == array([221., 60., 60., 0]))


def test_Freesurfer_04():
    region_label, approx = fs.find_brain_region([37, 48, 16])
    assert region_label == 'ctx-rh-parsorbitalis'
    assert approx == 0


def test_Freesurfer_05():
    region_label, approx = fs.find_brain_region([0, 0, 0], 2)
    assert region_label == '--not found--'
    assert approx == 2


def test_Freesurfer_06():
    region_label, approx = fs.find_brain_region([0, 0, 0], 5)
    assert region_label == 'Left-VentralDC'
    assert approx == 4


def test_Freesurfer_07():
    l0, l1, l2 = fs.read_label('lh')
    assert l0[-1] == 27
    assert l1.shape == (36, 5)
    assert l1[-1, -1] == 2146559
    assert l2[-1] == 'insula'
"""
