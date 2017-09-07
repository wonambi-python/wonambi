from pytest import raises

from wonambi.attr.chan import create_sphere_around_elec
from wonambi.attr import Freesurfer

from .paths import fs_path

def test_import_chan():
    with raises(ImportError):
        create_sphere_around_elec(None, None)


def test_import_anat():
    fs = Freesurfer(fs_path)
    with raises(ImportError):
        fs.surface_ras_shift
