from . import *

from glob import glob
from os import remove
from os.path import join, basename
from phypno.ioeeg import Ktlx
from phypno.ioeeg.ktlx import (_read_ent, _read_etc, _read_snc, _read_erd,
                               _read_eeg, _read_vtc, cache_dir)

ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
sine_dir = join(data_dir, 'MGXX/eeg/raw/xltek/sine1')


@raises(FileNotFoundError)
def test_sine_dir():
    lg.info('---\nfunction: ' + stack()[0][3])
    Ktlx(sine_dir)
