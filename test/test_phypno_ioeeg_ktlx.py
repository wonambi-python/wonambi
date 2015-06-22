from nose.tools import raises
from os.path import abspath, join

from phypno.ioeeg import Ktlx
from phypno.ioeeg.ktlx import (_read_ent, _read_etc, _read_snc,
                               _read_eeg, _read_vtc)

import phypno
data_dir = abspath(join(phypno.__path__[0], '..', 'data'))


ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
sine_dir = join(data_dir, 'MGXX/eeg/raw/xltek/sine1')


@raises(FileNotFoundError)
def test_sine_dir():
    Ktlx(sine_dir)


def test_read_ent():
    k = Ktlx(ktlx_dir)
    _read_ent(join(k.filename, k._basename + '.ent'))


def test_read_eeg():
    k = Ktlx(ktlx_dir)
    _read_eeg(join(k.filename, k._basename + '.eeg'))


def test_read_etc():
    k = Ktlx(ktlx_dir)
    _read_etc(join(k.filename, k._basename + '.etc'))


def test_read_snc():
    k = Ktlx(ktlx_dir)
    _read_snc(join(k.filename, k._basename + '.snc'))


def test_read_vtc():
    k = Ktlx(ktlx_dir)
    _read_vtc(join(k.filename, k._basename + '.vtc'))
