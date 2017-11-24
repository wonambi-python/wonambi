from numpy import isnan
from pytest import raises
from wonambi import Dataset

from .paths import ns2_file, ns4_file, nev_file


def test_blackrock_ns4_00():
    d = Dataset(ns4_file)
    data = d.read_data(begsam=10, endsam=11)
    assert data.data[0][0, 0] == 3463.0878627887814


def test_blackrock_ns4_01():
    d = Dataset(ns4_file)
    data = d.read_data(begsam=-10, endsam=1)
    assert isnan(data.data[0][0, :10]).all()


def test_blackrock_ns4_02():
    d = Dataset(ns4_file)

    d = Dataset(ns4_file)
    N_SMP = d.header['n_samples']
    data = d.read_data(begsam=N_SMP - 1, endsam=N_SMP + 10)
    assert isnan(data.data[0][0, -10:]).all()


def test_blackrock_markers_00():
    d = Dataset(ns2_file)
    markers = d.read_markers()
    assert len(markers) == 176


def test_blackrock_nev():
    d = Dataset(nev_file)
    with raises(TypeError):
        d.read_data()
