from wonambi import Dataset

from .paths import micromed_file



def test_micromed_header():
    d = Dataset(micromed_file)
    assert d.header['chan_name'][-1] == 'EMG'
