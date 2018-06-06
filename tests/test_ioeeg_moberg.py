from numpy import isnan

from wonambi import Dataset

from .paths import moberg_file


def test_ioeeg_mobert_begin():
    d = Dataset(moberg_file)
    data = d.read_data(begsam=-10, endsam=10)

    assert isnan(data(trial=0, chan='Fp1')[0])
    assert data(trial=0, chan='Fp1')[-1] == -1678.8678197860718


def test_ioeeg_mobert_end():
    d = Dataset(moberg_file)
    n_smp = d.header['n_samples']
    data = d.read_data(begsam=n_smp - 1, endsam=n_smp + 1)

    assert data(trial=0, chan='Fp1')[0] == -12302.22384929657
    assert isnan(data(trial=0, chan='Fp1')[1])

    assert len(d.read_markers()) == 0
