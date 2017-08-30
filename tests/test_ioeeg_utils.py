from numpy import (append,
                   arange,
                   array,
                   cumsum,
                   empty,
                   isnan,
                   NaN
                   )
from numpy.testing import assert_array_equal
from pytest import raises

from wonambi.ioeeg.utils import _select_blocks


BLOCKS = array([5, 11, 6, 7, 12])


def test_select_block_first_block():
    _assert_begsam_endsam(0, 2)


def test_select_block_second_block():
    _assert_begsam_endsam(5, 9)


def test_select_block_multiple_blocks():
    _assert_begsam_endsam(3, 38)


def test_select_block_empty():
    dat = _assert_begsam_endsam(1, 1)
    assert dat.shape[0] == 0


def test_select_block_begsam_before():
    dat = _assert_begsam_endsam(-10, 1)
    assert dat.shape[0] == 11
    assert isnan(dat[0])


def test_select_block_endsam_after():
    dat = _assert_begsam_endsam(10, 45)
    assert dat.shape[0] == 35
    assert isnan(dat[-1])


def test_select_block_endsam_before():
    with raises(StopIteration):
        next(_select_blocks(BLOCKS, -10, -5))


def test_select_block_begsam_after():
    with raises(StopIteration):
        next(_select_blocks(BLOCKS, 50, 55))


def _assert_begsam_endsam(begsam, endsam):

    dat_on_disk, intervals = _generate_dat_on_disk()

    expected_dat = arange(begsam, endsam).astype('float')
    expected_dat[(expected_dat < 0) & (expected_dat > intervals[-1])] = NaN

    dat = empty(endsam - begsam)
    dat.fill(NaN)

    for i_dat, blk, i_blk in _select_blocks(BLOCKS, begsam, endsam):
        # print('{: 3d}-{: 3d} = {: 3d}: {: 3d}-{: 3d}'.format(i_dat[0], i_dat[1], blk, i_blk[0], i_blk[1]))
        dat[i_dat[0]:i_dat[1]] = dat_on_disk[blk][i_blk[0]:i_blk[1]]

    return dat

    assert_array_equal(expected_dat, dat)


def _generate_dat_on_disk():
    intervals = cumsum(append(0, BLOCKS))

    dat_on_disk = []
    for i in range(len(intervals) - 1):
        dat_on_disk.append(arange(intervals[i], intervals[i + 1]))

    return dat_on_disk, intervals
