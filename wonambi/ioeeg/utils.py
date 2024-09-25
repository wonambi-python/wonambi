from datetime import datetime
from numpy import (append,
                   cumsum,
                   where,
                   ndarray,
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
        return None

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

    try:
        labels = hdf5_labels.value.flat
    except:
        labels = hdf5_labels[()].flat
    for l in labels:
        chan_name.append(read_hdf5_str(f[l]))
    return chan_name


def read_hdf5_str(value):
    try:
        data = value[()]
        if isinstance(data, bytes):
            datfile = data.decode('utf-8')  
        elif isinstance(data, str):
            datfile = data  
        elif isinstance(data, ndarray):
            if data.dtype.kind in ('S', 'O'):  
                
                datfile = ''.join([x.decode('utf-8') if isinstance(x, bytes) else str(x) for x in data])
            elif data.dtype.kind in ('i', 'u'):  # Integer types
                
                datfile = ''.join([chr(int(x)) for x in data])
            else:
                datfile = str(data)
        else:
            datfile = str(data)
    except:
        try:
            datfile = ''.join([chr(str(x)) for x in value.value])
        except:
            datfile = ''.join([chr(x[0]) for x in value])
    if datfile == '\x00\x00':
        return ''
    else:
        return datfile
    
