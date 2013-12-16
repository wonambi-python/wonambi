"""Module to cache the file in memory, so that you don't read it many times.

"""

from logging import getLogger
from tempfile import mkdtemp
from joblib import Memory
from nibabel import load

lg = getLogger(__name__)

cachedir = mkdtemp()
lg.info(cachedir)
memory = Memory(cachedir=cachedir, verbose=0)


@memory.cache
def read_filebytes(binary_file):
    lg.info('Reading file: ' + binary_file)
    with open(binary_file, 'rb') as f:
        filebytes = f.read()
    return filebytes

@memory.cache
def read_seg(seg_file):
    seg_mri = load(seg_file)
    seg_aff = seg_mri.get_affine()
    seg_dat = seg_mri.get_data()
    return seg_dat, seg_aff
