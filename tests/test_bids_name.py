from wonambi.bids.structure import BIDSName
from .paths import BIDS_IEEG_CHANNELS


def test_bids_name():
    b = BIDSName(BIDS_IEEG_CHANNELS)
    assert b.values['sub'] == 'som682'
    assert b.extension == '.tsv'
    assert b.format == 'channels'

    assert b.filename == b._filename
