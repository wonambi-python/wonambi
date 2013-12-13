"""Module to work with channels.

It provides a general class to work with channels. Channels is the general term
that refers to the points where signal comes from, it's an abstract concept.
Electrodes, magnetometer, axiometers and gradiometers are the actual recording
devices measuring the signal. For example, in the case of EEG, you need two
electrodes to have one signal, where one signal is the difference between the
two electrodes.

In other words, the channel is where you want to plot the signal.

"""
from os.path import splitext
from numpy import zeros
from ..utils import UnrecognizedFormat


def detect_format(filename):
    """Detect file format of the channels based on extension.

    Parameters
    ----------
    filename : str
        name of the filename

    Returns
    -------
    str
        file format

    """
    if splitext(filename)[1] == '.csv':
        recformat = 'csv'
    else:
        recformat = 'unknown'

    return recformat


def _read_csv(elec_file):
    chan_label = []
    num_lines = sum(1 for line in open(elec_file))
    chan_pos = zeros((num_lines, 3))

    with open(elec_file, 'r') as f:
        for i, l in enumerate(f):
            a, b, c, d = [t(s) for t, s in zip((str, float, float, float),
                          l.split(','))]
            chan_label.append(a)
            chan_pos[i, :] = [b, c, d]

    return chan_label, chan_pos


class Chan():
    """Provide class Chan, generic class for channel location.

    Parameters
    ----------
    chan_input : various formats
        information about the channels.
        Possible formats are: csv of format: label, x-pos, y-pos, z-pos

    Attributes
    ----------
    chan_name : list
        the name of the channel
    xy : numpy.ndarray
        location in 2D, with shape (2, n_chan, d)
    xyz : numpy.ndarray
        location in 3D, with shape (3, n_chan, d)

    Raises
    ------
    UnrecognizedFormat
        If the format is not recognized

    """

    def __init__(self, chan_input):
        format_ = detect_format(chan_input)  # TODO: if file at all
        self.xy = None

        if format_ == 'csv':
            self.chan_name, self.xyz = _read_csv(chan_input)
        else:
            raise UnrecognizedFormat('Unrecognized format ("' + format_ + '")')

    def n_chan(self):
        """Returns the number of channels.

        """
        return len(self.chan_name)
