from numpy import isnan

from wonambi import Dataset
from wonambi.ioeeg import write_edf
from wonambi.utils import create_data

from .paths import (psg_file,
                    generated_file,
                    EXPORTED_PATH,
                    )


psg = Dataset(psg_file)
generated = Dataset(generated_file)


def test_edf_read():
    psg.read_data(begtime=10, endtime=20)
    markers = psg.read_markers()
    assert len(markers) == 0


def test_edf_before_start_both():
    data = psg.read_data(begsam=-100, endsam=-10)
    assert isnan(data.data[0][0, 0])


def test_edf_before_start():
    data = psg.read_data(begsam=-100, endsam=10)
    assert isnan(data.data[0][0, 0])


def test_edf_after_end():
    n_samples = psg.header['n_samples']
    data = psg.read_data(begsam=n_samples - 100, endsam=n_samples + 100)
    assert isnan(data.data[0][0, -1])


def test_edf_annot():
    markers = generated.read_markers()
    assert len(markers) == 2


def test_edf_write():
    data = create_data()
    write_edf(data, EXPORTED_PATH / 'export.edf')
