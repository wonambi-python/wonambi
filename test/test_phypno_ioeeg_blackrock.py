from nose.tools import raises
from os.path import abspath, join

from phypno.ioeeg import Ktlx

import phypno
data_dir = abspath(join(phypno.__path__[0], '..', 'data'))

ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
sine_dir = join(data_dir, 'MGXX/eeg/raw/xltek/sine1')


@raises(FileNotFoundError)
def test_sine_dir():
    Ktlx(sine_dir)
