from wonambi import Dataset

from .paths import micromed_file


def test_dataset_events():
    d = Dataset(micromed_file)
    events = [ev['start'] for ev in d.read_markers()][::30]

    data = d.read_data(events=events)

    assert data.time[0].shape[0] == 512
    assert data.time[0].shape[0] == data.data[0].shape[1]
    assert (data.number_of('time') == 512).all()
