from datetime import datetime
from numpy import (append,
                   cumsum,
                   where,
                   )


DEFAULT_DATETIME = datetime(2000, 1, 1)


def decode(s):
    return s.decode('utf-8', errors='replace')


def _select_blocks(blocks, begsam, endsam):
    """Convenience function to use when reading data stored in blocks on disk
    (f.e. edf).

    Parameters
    ----------
    blocks : ndarray
        vector with number of samples in each block
    begsam : int
        first sample of interest (included)
    endsam : int
        last sample of interest (excluded)

    Yields
    ------
    dat_index : tuple
        start and end position to index the output data
    blk : int
        index of the block to read
    blk_index : tuple
        start and end position to index the current block

    Raises
    ------
    StopIteration
        when endsam is before start of the data or begsam is after the end of
        the data.
    """
    intervals = cumsum(append(0, blocks))

    try:
        begblk = max(where(begsam < intervals)[0][0] - 1, 0)
        endblk = min(where(endsam > intervals)[0][-1], len(blocks) - 1)
    except IndexError:
        raise StopIteration

    for blk in range(begblk, endblk + 1):

        beg_in_blk = max(begsam - intervals[blk], 0)
        end_in_blk = min(endsam - intervals[blk], blocks[blk])

        beg_in_dat = beg_in_blk - begsam + intervals[blk]
        end_in_dat = end_in_blk - begsam + intervals[blk]

        yield (beg_in_dat, end_in_dat), blk, (beg_in_blk, end_in_blk)


def read_hdf5_chan_name(f, hdf5_labels):
    # some hdf5 magic
    # https://groups.google.com/forum/#!msg/h5py/FT7nbKnU24s/NZaaoLal9ngJ
    chan_name = []
    for l in hdf5_labels.value.flat:
        chan_name.append(read_hdf5_str(f[l]))
    return chan_name


def read_hdf5_str(value):
    datfile = ''.join([chr(x) for x in value.value])
    if datfile == '\x00\x00':
        return ''
    else:
        return datfile
