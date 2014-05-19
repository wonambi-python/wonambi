from . import *

from glob import glob
from os import remove
from os.path import join, basename
from phypno.ioeeg import Ktlx
from phypno.ioeeg.ktlx import (_read_ent, _read_etc, _read_snc, _read_erd,
                               _read_eeg, _read_vtc, temp_dir)

ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
sine_dir = join(data_dir, 'MGXX/eeg/raw/xltek/sine1')


@raises(FileNotFoundError)
def test_sine_dir():
    lg.info('---\nfunction: ' + stack()[0][3])
    Ktlx(sine_dir)


def test_sine_erd():
    lg.info('---\nfunction: ' + stack()[0][3])
    sinewave = glob(join(sine_dir, '*.erd'))[0]
    remove(join(temp_dir, basename(sinewave)))

    _read_erd(sinewave, 10)  # new file
    _read_erd(sinewave, 10)  # memory-mapped file


def test_read_ent():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_ent(join(k.filename, k._basename + '.ent'))


def test_read_eeg():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_eeg(join(k.filename, k._basename + '.eeg'))


def test_read_etc():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_etc(join(k.filename, k._basename + '.etc'))


def test_read_snc():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_snc(join(k.filename, k._basename + '.snc'))


def test_read_vtc():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_vtc(join(k.filename, k._basename + '.vtc'))
