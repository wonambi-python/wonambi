"""Module to cache the file in memory, so that you don't read it many times.

"""

from logging import getLogger
from tempfile import mkdtemp
from nibabel import load

lg = getLogger(__name__)

cachedir = mkdtemp()
lg.info(cachedir)

try:
    from joblib import Memory
except ImportError:
    class Memory:
        def __init__(self, cachedir=None, verbose=None):
            pass

        def cache(self, func):
            return func

memory = Memory(cachedir=cachedir, verbose=0)


@memory.cache
def read_seg(seg_file):
    seg_mri = load(seg_file)
    seg_aff = seg_mri.get_affine()
    seg_dat = seg_mri.get_data()
    return seg_dat, seg_aff
