from wonambi.ioeeg.edf import _select_blocks
from pathlib import Path

from struct import unpack


HDR_LENGTH = 1024
from numpy import dtype, array, ones

x = f.read(1024)

next(_select_blocks(blocks, 10000, 10500))
_read_record_continuous(filename, 1000)


def _read_record_continuous(filename, i_block):

    with filename.open('rb') as f:
        f.seek(HDR_LENGTH + i_block * 2070)
        v = unpack('<qHH' + 1024 * 'h' + 10 * 'B', f.read(2070))

    return v[3:-10]
