from wonambi import Dataset
from pytest import raises
from bidso.utils import replace_underscore

from .paths import micromed_file, bids_dir

bids_dir.mkdir(exist_ok=True, parents=True)
# TODO: we should generate the name
bids_file = bids_dir / 'sub-test_task-unknown_run-1_ieeg.eeg'


def test_ioeeg_bids_write():

    d = Dataset(micromed_file)
    data = d.read_data()
    markers = d.read_markers()
    data.export(bids_file, 'bids', markers=markers)

    d_bids = Dataset(bids_file, bids=True)
    data_bids = d_bids.read_data()
    markers_bids = d_bids.read_markers()

    assert len(markers) == len(markers_bids)
    assert markers[0]['start'] == markers_bids[0]['start']

    assert data.data[0][0, 0] == data_bids.data[0][0, 0]


def test_ioeeg_bids_multiple_freq():

    # change one channel frequency
    with replace_underscore(bids_file, 'channels.tsv').open('r+') as f:
        f.seek(88)
        f.write('9')

    with raises(ValueError):
        Dataset(bids_file, bids=True)
