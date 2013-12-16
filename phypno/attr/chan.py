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


def export_csv(chan, elec_file):
    """Write the elec coordinates into a csv file.

    Parameters
    ----------
    chan : instance of class Chan
        the definition of the channels
    elec_file : str
        path to file where to save csv

    """
    with open(elec_file, 'w') as f:
        for i, l in enumerate(chan.chan_name):
            line = "%s, %.1f, %.1f, %.1f\n" % (l, chan.xyz[i, 0],
                                               chan.xyz[i, 1],
                                               chan.xyz[i, 2])
            f.write(line)


class Chan():
    """Provide class Chan, generic class for channel location.

    You can read from a file, and then you pass only one argument.
    Or you can directly assign the chan names and the coordinates.

    Parameters
    ----------
    chan_input : various formats
        information about the channels.
          - csv of format: label, x-pos, y-pos, z-pos

    Parameters
    ----------
    chan_name : list of str
        the name of the channel
    coords : numpy.ndarray
       location in 3D, with shape (3, n_chan)

    Attributes
    ----------
    chan_name : list of str
        the name of the channel
    xy : numpy.ndarray
        location in 2D, with shape (2, n_chan)
    xyz : numpy.ndarray
        location in 3D, with shape (3, n_chan)

    Raises
    ------
    UnrecognizedFormat
        If the format is not recognized

    """

    def __init__(self, *args):
        self.xy = None

        if len(args) == 1:
            format_ = detect_format(args[0])
            if format_ == 'csv':
                self.chan_name, self.xyz = _read_csv(args[0])
            else:
                raise UnrecognizedFormat('Unrecognized format ("' + format_ +
                                         '")')

        elif len(args) == 2:
            self.chan_name = args[0]
            self.xyz = args[1]

    def n_chan(self):
        """Returns the number of channels.

        """
        return len(self.chan_name)

    def assign_region(self, anat, chan_name=None, approx=3):
        """Assign a brain region based on the channel location.

        Parameters
        ----------
        anat : instance of phypno.attr.anat.Freesurfer
            anatomical information taken from freesurfer.
        chan_name : str, optional
            the channel name
        approx : int
            approximation to define position of the electrode.

        Returns
        -------
        region : str
            the label of the region in which the electrode is located.

        """
        if chan_name:
            idx_ch = self.chan_name.index(chan_name)
            chan_pos = self.xyz[idx_ch, :]
            region, _ = anat.find_brain_region(chan_pos)
            return region

    def export(self, elec_file):
        """Export channel name and location to file.

        Parameters
        ----------
        elec_file : str
            path to file where to save csv

        """
        ext = splitext(elec_file)[1]
        if ext == '.csv':
            export_csv(self, elec_file)
