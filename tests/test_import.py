from pytest import raises

from wonambi.attr.chan import create_sphere_around_elec
from wonambi.attr import Freesurfer, Surf
from wonambi.source import Morph
from wonambi.utils import create_data

from .paths import (fs_path,
                    surf_path,
                    )

fs = Freesurfer(fs_path)
data = create_data()
surf = Surf(surf_path)


def test_import_chan():
    with raises(ImportError):
        create_sphere_around_elec(None, '')


def test_import_anat():
    with raises(ImportError):
        fs.surface_ras_shift

    with raises(ImportError):
        fs.read_label('')

    with raises(ImportError):
        fs.read_seg()


def test_import_morph():
    with raises(ImportError):
        morph = Morph(from_surf=surf)
        morph(data)


def test_scroll_data():
    with raises(ImportError):
        from wonambi.scroll_data import MainWindow
