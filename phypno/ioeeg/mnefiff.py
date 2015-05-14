from logging import getLogger, WARNING
lg = getLogger(__name__)


def write_mnefiff(data, filename):
    """Export data to MNE using FIFF format.

    Parameters
    ----------
    data : instance of ChanTime
        data with only one trial
    filename : path to file
        file to export to (include '.mat')

    Notes
    -----
    It cannot store data larger than 2 GB.
    The data is assumed to have only EEG electrodes.
    It overwrites a file if it exists.
    """
    from mne import create_info, set_log_level
    from mne.io import RawArray

    set_log_level(WARNING)

    TRIAL = 0
    info = create_info(list(data.axis['chan'][TRIAL]), data.s_freq, ['eeg', ] *
                       data.number_of('chan')[TRIAL])

    UNITS = 1e-6  # mne wants data in uV
    fiff = RawArray(data.data[0] * UNITS, info)

    if data.attr['chan']:
        fiff.set_channel_positions(data.attr['chan'].return_xyz(),
                                   data.attr['chan'].return_label())

    fiff.save(filename, overwrite=True)
