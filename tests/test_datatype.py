from pickle import load, dump
from tempfile import NamedTemporaryFile
from numpy.testing import assert_array_equal

from wonambi.trans import math
from wonambi.utils import create_data


def test_pickle_01():
    data = create_data()

    tmpfile = NamedTemporaryFile(delete=False)
    with tmpfile as f:
        dump(data, f)

    with open(tmpfile.name, 'rb') as f:
        loaded = load(f)

    assert_array_equal(data.axis['time'][0], loaded.time[0])


def test_copy_axis():
    """Sometimes we remove an axis. So when we copy it, we need to make sure
    that the new dataset doesn't have the removed axis.
    """
    # remove one axis
    data = create_data()
    data = math(data, axis='chan', operator_name='mean')
    assert len(data.axis) == 1

    output = data._copy(axis=True)
    assert len(data.axis) == len(output.axis)

    output = data._copy(axis=False)
    assert len(data.axis) == len(output.axis)
