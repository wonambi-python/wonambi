"""Module to work with channels.

It provides a general class to work with channels. Channels is the general term
that refers to the points where signal comes from, it's an abstract concept.
Electrodes, magnetometer, axiometers and gradiometers are the actual recording
devices measuring the signal. For example, in the case of EEG, you need two
electrodes to have one signal, where one signal is the difference between the
two electrodes.

In other words, the channel is where you want to plot the signal.

"""
from logging import getLogger
from os.path import splitext
from numpy import zeros
from ..utils import UnrecognizedFormat

lg = getLogger(__name__)


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
        location in 2D, with shape (n_chan, 2)
    xyz : numpy.ndarray
        location in 3D, with shape (n_chan, 3)

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
            if args[1].shape[1] == 3:
                self.xyz = args[1]
            else:
                raise ArithmeticError('Incorrect shape: the second dimension '
                                      'should be 3, not ' +
                                      str(args[1].shape[1]))

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
            chan_pos = self.return_chan_xyz(chan_name)
            region, _ = anat.find_brain_region(chan_pos, approx)
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

    def find_chan_in_region(self, anat, region_name):
        """Find which channels are in a specific region.

        Parameters
        ----------
        anat : instance of phypno.attr.anat.Freesurfer
            anatomical information taken from freesurfer.
        region_name : str
            the name of the region, according to FreeSurferColorLUT.txt

        Returns
        -------
        chan_in_region : list of str
            list of the channels that are in one region.

        Notes
        -----
        It can be made more fuzzy, for example, by using regex.

        """
        chan_in_region = []
        for chan in self.chan_name:
            region = self.assign_region(anat, chan)
            if region_name in region:
                lg.debug('{}: region {} matches search pattern {}'.format(chan,
                         region, region_name))
                chan_in_region.append(chan)

        return chan_in_region

    def return_chan_xyz(self, chan_name):
        """Returns the location in xyz for a particular channel name.

        Parameters
        ----------
        chan_name : str
            the name of one channel.

        Returns
        -------
        chan_xyz : numpy.ndarray
            a 3x0 vector with the position of a channel.

        """
        return self.xyz[self.chan_name.index(chan_name), :]
