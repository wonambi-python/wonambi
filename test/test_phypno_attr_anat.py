from nose.tools import raises
from os.path import abspath, join


import phypno
data_dir = abspath(join(phypno.__path__[0], '..', 'data'))

# lg.info('I do not know how to test for importerror of nibabel')

from os import environ
from os.path import join
from numpy import array
from phypno.attr import Freesurfer, Surf
from phypno.attr.anat import import_freesurfer_LUT

fs_dir = join(data_dir, 'MGXX/mri/proc/freesurfer')
FREESURFER_HOME = environ['FREESURFER_HOME']


def test_import_freesurfer_LUT_01():
    import_freesurfer_LUT()


@raises(OSError)
def test_import_freesurfer_LUT_02():
    del environ['FREESURFER_HOME']
    import_freesurfer_LUT()

environ['FREESURFER_HOME'] = FREESURFER_HOME


def test_import_freesurfer_LUT_03():
    import_freesurfer_LUT(join(FREESURFER_HOME, 'FreeSurferColorLUT.txt'))


@raises(FileNotFoundError)
def test_import_freesurfer_LUT_04():
    import_freesurfer_LUT(join(data_dir, 'does_not_exist'))


def test_Surf_01():
    Surf(join(fs_dir, 'surf', 'lh' + '.' + 'pial'))


def test_Surf_02():
    Surf(join(fs_dir, 'bem', 'freesurfer-outer_skin.surf'))


@raises(OSError)
def test_Freesurfer_01():
    Freesurfer('')


def test_Freesurfer_02():
    Freesurfer(fs_dir, join(data_dir, 'does_not_exist'))


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
