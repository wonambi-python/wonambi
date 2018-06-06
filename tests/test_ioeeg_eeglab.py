from numpy import isnan

from wonambi import Dataset

from .paths import (eeglab_1_file,
                    eeglab_2_file,
                    eeglab_hdf5_1_file,
                    eeglab_hdf5_2_file,
                    )


def test_ioeeg_eeglab():

    d1 = Dataset(eeglab_1_file)
    d2 = Dataset(eeglab_2_file)

    data1 = d1.read_data()
    data2 = d2.read_data()

    assert data1.data[0][0, 0] == data2.data[0][0, 0]

    assert len(d1.read_markers()) == 2


def test_ioeeg_eeglab_begsam():

    d1 = Dataset(eeglab_1_file)
    data = d1.read_data(begsam=-10, endsam=1)
    assert isnan(data.data[0][0, 0])


def test_ioeeg_eeglab_hdf5():

    d1 = Dataset(eeglab_hdf5_1_file)
    d2 = Dataset(eeglab_hdf5_2_file)

    data1 = d1.read_data(begsam=100, endsam=200)
    data2 = d2.read_data(begsam=100, endsam=200)

    assert data1.data[0][0, 0] == data2.data[0][0, 0]

    assert len(d1.read_markers()) == 2
