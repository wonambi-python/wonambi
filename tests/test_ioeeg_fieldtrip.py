from numpy.testing import assert_array_equal
from pytest import raises

from wonambi import Dataset
from wonambi.ioeeg import fieldtrip
from wonambi.utils import create_data

from .paths import (fieldtrip_file,
                    hdf5_file,
                    )


def test_write_read_fieldtrip():
    data = create_data(n_trial=1, n_chan=2)

    data.export(fieldtrip_file, export_format='fieldtrip')
    d = Dataset(fieldtrip_file)
    ftdata = d.read_data()
    assert_array_equal(data.data[0], ftdata.data[0])

    assert len(d.read_markers()) == 0


def test_write_read_fieldtrip_hdf5():
    d = Dataset(hdf5_file)
    d.read_data()


def test_wrong_variable_name():
    fieldtrip.VAR = 'unknown'
    with raises(KeyError):
        Dataset(fieldtrip_file)

    with raises(KeyError):
        Dataset(hdf5_file)
