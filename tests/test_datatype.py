from wonambi.utils import create_data
from pickle import load, dump
from tempfile import NamedTemporaryFile
from numpy.testing import assert_array_equal


def test_pickle_01():
    data = create_data()

    tmpfile = NamedTemporaryFile(delete=False)
    with tmpfile as f:
        dump(data, f)

    with open(tmpfile.name, 'rb') as f:
        loaded = load(f)

    assert_array_equal(data.axis['time'][0], loaded.time[0])
