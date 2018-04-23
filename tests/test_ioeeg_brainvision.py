from numpy import isnan
from numpy.testing import assert_almost_equal
from pytest import raises

from wonambi import Dataset
from wonambi.ioeeg.brainvision import _parse_ini

from .paths import brainvision_dir


def test_brainvision_dataset_01():
    d = Dataset(brainvision_dir / 'test.vhdr')
    data = d.read_data(begtime=1, endtime=2)

    assert data.data[0][0, 0] == -24.0
    assert len(d.read_markers()) == 12

    data = d.read_data(begsam=-1, endsam=5)
    assert isnan(data.data[0][0, 0])


def test_brainvision_dataset_02():
    d = Dataset(brainvision_dir / 'test_old_layout_latin1_software_filter.vhdr')
    data = d.read_data(begsam=1, endsam=2)
    assert_almost_equal(data.data[0][0, 0], 5.1)

    data = d.read_data(endsam=255)
    assert isnan(data.data[0][0, -1])

    data = d.read_data()
    assert data.data[0].shape == (29, 251)


def test_brainvision_parseini():
    for vhdr_file in brainvision_dir.glob('*.vhdr'):
        _parse_ini(vhdr_file)

    for vmrk_file in brainvision_dir.glob('*.vmrk'):
        _parse_ini(vmrk_file)

    with raises(ValueError):
        _parse_ini(brainvision_dir / 'wrongheader.ini')
