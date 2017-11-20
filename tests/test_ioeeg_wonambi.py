from numpy.testing import assert_array_equal

from wonambi import Dataset
from wonambi.ioeeg import write_wonambi
from wonambi.utils import create_data

from .paths import wonambi_file

gen_data = create_data(n_trial=1)


def test_wonambi_write_read():
    write_wonambi(gen_data, wonambi_file, subj_id='test_subj')
    d = Dataset(wonambi_file)
    data = d.read_data()
    assert_array_equal(data(trial=0), gen_data(trial=0))
