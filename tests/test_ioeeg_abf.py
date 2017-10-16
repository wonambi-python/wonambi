from numpy import isnan

from wonambi import Dataset

from .paths import axon_abf_file


d = Dataset(axon_abf_file)


def test_abf_read():
    assert len(d.header['chan_name']) == 1
    assert d.header['start_time'].minute == 47

    data = d.read_data(begtime=1, endtime=2)

    assert data.data[0][0, 0] == 2.1972655922581912

    markers = d.read_markers()
    assert len(markers) == 0


def test_abf_boundary():
    data = d.read_data(begsam=-10, endsam=5)
    assert isnan(data.data[0][0, :10]).all()

    n_smp = d.header['n_samples']
    data = d.read_data(begsam=n_smp - 2, endsam=n_smp + 10)
    assert isnan(data.data[0][0, 2:]).all()
