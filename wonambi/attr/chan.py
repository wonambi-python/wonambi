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
from pathlib import Path
from numpy import asarray, ndindex, zeros
from numpy.linalg import norm
from re import match

from ..utils import UnrecognizedFormat, MissingDependency

try:
    from nibabel import load as nload
    from nibabel.affines import apply_affine
except ImportError as err:
    nload = apply_affine = MissingDependency(err)


lg = getLogger(__name__)

mu = '\N{GREEK SMALL LETTER MU}'


def _convert_unit(unit):
    """Convert different names into SI units.

    Parameters
    ----------
    unit : str
        unit to convert to SI

    Returns
    -------
    str
        unit in SI format.

    Notes
    -----
    SI unit such as mV (milliVolt, mVolt), μV (microVolt, muV).

    """
    if unit is None:
        return ''

    prefix = None
    suffix = None
    if unit[:5].lower() == 'milli':
        prefix = 'm'
        unit = unit[5:]
    elif unit[:5].lower() == 'micro':
        prefix = mu
        unit = unit[5:]
    elif unit[:2].lower() == 'mu':
        prefix = mu
        unit = unit[2:]

    if unit[-4:].lower() == 'volt':
        suffix = 'V'
        unit = unit[:-4]

    if prefix is None and suffix is None:
        unit = unit
    elif prefix is None and suffix is not None:
        unit = unit + suffix
    elif prefix is not None and suffix is None:
        unit = prefix + unit
    else:
        unit = prefix + suffix

    return unit


def _read_separated_values(elec_file, sep):
    """

    TODO
    ----
    add documentation to _read_separated_values
    """
    elec_file = Path(elec_file)

    chan_label = []
    with elec_file.open() as f:
        num_lines = sum(1 for line in f)
    chan_pos = zeros((num_lines, 3))

    with elec_file.open('r') as f:
        for i, l in enumerate(f):
            a, b, c, d = [t(s) for t, s in zip((str, float, float, float),
                          l.split(sep))]
            chan_label.append(a)
            chan_pos[i, :] = [b, c, d]

    return chan_label, chan_pos


def detect_format(filename):
    """Detect file format of the channels based on extension.

    Parameters
    ----------
    filename : Path
        name of the filename

    Returns
    -------
    str
        file format
    """
    filename = Path(filename)

    if filename.suffix == '.csv':
        recformat = 'csv'
    elif filename.suffix == '.sfp':
        recformat = 'sfp'

    else:
        recformat = 'unknown'

    return recformat


class Chan():
    """Provide class Chan, for individual channels.

    Parameters
    ----------
    label : str
        name of the channel
    xyz : numpy.ndarray or list or tuple
        1d vector of 3 elements
    chtype : str, optional
        channel type (can be any string)
    unit : str, optional
        units, using SI
    attr : dict
        dictionary where you can store additional information per channel. Use
        chan.attr.update({'new_key': new_value})
    """
    def __init__(self, label, xyz=None, unit=None, attr=None):
        self.label = label
        self.xyz = asarray(xyz)
        self.unit = _convert_unit(unit)
        if attr is None:
            self.attr = {}
        else:
            self.attr = attr


class Channels():
    """Provide class Chan, generic class for channel location.

    You can read from a file, and then you pass only one argument.
    Or you can directly assign the chan names and the coordinates.

    Parameters
    ----------
    chan : list of instance of Chan
        list of channels (which are instances of Chan)

    Parameters
    ----------
    chan_input : various formats
        information about the channels

    Parameters
    ----------
    labels : list of str
        the name of the channel
    coords : numpy.ndarray
       location in 3D, with shape (n_chan, 3)

    Attributes
    ----------
    chan : list of instance of wonambi.attr.chan.Chan
        list of channels

    Raises
    ------
    UnrecognizedFormat
        If the format is not recognized

    Notes
    -----
    chan_input can be a csv file without header and with format:
    label, x-pos, y-pos, z-pos
    or an sfp file without header and with format:
    label x-pos y-pos z-pos
    """
    def __init__(self, *args):

        if len(args) == 1 and isinstance(args[0], list):
            self.chan = args[0]
        else:
            self.chan = []

            labels = None
            xyz = None

            if len(args) == 1:
                format_ = detect_format(args[0])
                if format_ == 'csv':
                    labels, xyz = _read_separated_values(args[0], ',')
                elif format_ == 'sfp':
                    labels, xyz = _read_separated_values(args[0], ' ')
                else:
                    raise UnrecognizedFormat('Unrecognized format ("' +
                                             format_ + '")')

            elif len(args) == 2:
                labels = args[0]
                if args[1].shape[1] == 3:
                    xyz = args[1]
                else:
                    raise ValueError('Incorrect shape: the second dimension '
                                     'should be 3, not ' +
                                     str(args[1].shape[1]))

            for idx, one_label in enumerate(labels):
                self.chan.append(Chan(one_label, xyz[idx, :]))

    def __call__(self, func=None):
        """Return a new instance of Channels, with a subset of channels.

        Parameters
        ----------
        func : function
            function to execute on each instance of Chan, should return True or
            False (include the channel or not).

        Returns
        -------
        new instance of Channels
            new instance of Channels, but instances of Chan are not deep-copied

        """
        chans = []
        for one_chan in self.chan:
            if func(one_chan):
                chans.append(one_chan)

        return Channels(chans)

    def return_label(self):
        """Returns the labels for all the channels.

        Returns
        -------
        list of str
            list of the channel labels.
        """
        return [x.label for x in self.chan]

    def return_xy(self, labels=None):
        """Returns the location in xy for some channels.

        Parameters
        ----------
        labels : list of str, optional
            the names of the channels.

        Returns
        -------
        numpy.ndarray
            a 2xn vector with the position of a channel.

        Notes
        -----
        Simplest implementation. We should at least use project onto a 2D plane
        """
        xyz = self.return_xyz(labels=labels)
        xy = asarray(xyz)[:, 1:]
        return xy

    def return_xyz(self, labels=None):
        """Returns the location in xy for some channels.

        Parameters
        ----------
        labels : list of str, optional
            the names of the channels.

        Returns
        -------
        numpy.ndarray
            a 3xn vector with the position of a channel.
        """
        all_labels = self.return_label()

        if labels is None:
            labels = all_labels

        xyz = []
        for one_label in labels:
            idx = all_labels.index(one_label)
            xyz.append(self.chan[idx].xyz)

        return asarray(xyz)

    def return_attr(self, attr, labels=None):
        """return the attributes for each channels.

        Parameters
        ----------
        attr : str
            attribute specified in Chan.attr.keys()

        """
        all_labels = self.return_label()

        if labels is None:
            labels = all_labels

        all_attr = []
        for one_label in labels:
            idx = all_labels.index(one_label)
            try:
                all_attr.append(self.chan[idx].attr[attr])
            except KeyError:
                possible_attr = ', '.join(self.chan[idx].attr.keys())
                lg.debug('key "{}" not found, '.format(attr) +
                         'possible keys are {}'.format(possible_attr))
                all_attr.append(None)

        return all_attr

    @property
    def n_chan(self):
        """Returns the number of channels."""
        return len(self.chan)

    def export(self, elec_file):
        """Export channel name and location to file.

        Parameters
        ----------
        elec_file : Path or str
            path to file where to save csv
        """
        elec_file = Path(elec_file)
        if elec_file.suffix == '.csv':
            sep = ', '
        elif elec_file.suffix == '.sfp':
            sep = ' '

        with elec_file.open('w') as f:
            for one_chan in self.chan:
                values = ([one_chan.label, ] +
                          ['{:.3f}'.format(x) for x in one_chan.xyz])
                line = sep.join(values) + '\n'
                f.write(line)


def assign_region_to_channels(channels, anat, parc_type='aparc', max_approx=3,
                              exclude_regions=None):
    """Assign a brain region based on the channel location.

    Parameters
    ----------
    channels : instance of wonambi.attr.chan.Channels
        channels to assign regions to
    anat : instance of wonambi.attr.anat.Freesurfer
        anatomical information taken from freesurfer.
    parc_type : str
        'aparc', 'aparc.a2009s', 'BA', 'BA.thresh', or 'aparc.DKTatlas40'
        'aparc.DKTatlas40' is only for recent freesurfer versions
    max_approx : int, optional
        approximation to define position of the electrode.
    exclude_regions : list of str or empty list
        do not report regions if they contain these substrings. None means
        that it does not exclude any region. For example, to exclude white
        matter regions and unknown regions you can use
        exclude_regions=('White', 'WM', 'Unknown')

    Returns
    -------
    instance of wonambi.attr.chan.Channels
        same instance as before, now Chan have attr 'region'
    """
    for one_chan in channels.chan:
        one_region, approx = anat.find_brain_region(one_chan.xyz,
                                                    parc_type,
                                                    max_approx,
                                                    exclude_regions)
        one_chan.attr.update({'region': one_region, 'approx': approx})

    return channels


def find_chan_in_region(channels, anat, region_name):
    """Find which channels are in a specific region.

    Parameters
    ----------
    channels : instance of wonambi.attr.chan.Channels
        channels, that have locations
    anat : instance of wonambi.attr.anat.Freesurfer
        anatomical information taken from freesurfer.
    region_name : str
        the name of the region, according to FreeSurferColorLUT.txt

    Returns
    -------
    chan_in_region : list of str
        list of the channels that are in one region.
    """
    if 'region' not in channels.chan[0].attr.keys():
        lg.info('Computing region for each channel.')
        channels = assign_region_to_channels(channels, anat)

    chan_in_region = []
    for one_chan in channels.chan:
        if region_name in one_chan.attr['region']:
            chan_in_region.append(one_chan.label)

    return chan_in_region


def find_channel_groups(chan):
    """Channels are often organized in groups (different grids / strips or
    channels in different brain locations), so we use a simple heuristic to
    get these channel groups.

    Parameters
    ----------
    chan : instance of Channels
        channels to group

    Returns
    -------
    groups : dict
        channel groups: key is the common string, and the item is a list of
        labels
    """
    labels = chan.return_label()
    group_names = {match('([A-Za-z ]+)\d+', label).group(1) for label in labels}

    groups = {}
    for group_name in group_names:
        groups[group_name] = [label for label in labels if label.startswith(group_name)]

    return groups


def create_sphere_around_elec(xyz, template_mri, distance=8, freesurfer=None):
    """Create an MRI mask around an electrode location,

    Parameters
    ----------
    xyz : ndarray
        3x0 array
    template_mri : path or str (as path) or nibabel.Nifti
        (path to) MRI to be used as template
    distance : float
        distance in mm between electrode and selected voxels
    freesurfer : instance of Freesurfer
        to adjust RAS coordinates, see Notes

    Returns
    -------
    3d bool ndarray
        mask where True voxels are within selected distance to the electrode

    Notes
    -----
    Freesurfer uses two coordinate systems: one for volumes ("RAS") and one for
    surfaces ("tkReg", "tkRAS", and "Surface RAS"), so the electrodes might be
    stored in one of the two systems. If the electrodes are in surface
    coordinates (f.e. if you can plot surface and electrodes in the same space),
    then you need to convert the coordinate system. This is done by passing an
    instance of Freesurfer.
    """
    if freesurfer is None:
        shift = 0
    else:
        shift = freesurfer.surface_ras_shift

    if isinstance(template_mri, str) or isinstance(template_mri, Path):
        template_mri = nload(str(template_mri))

    mask = zeros(template_mri.shape, dtype='bool')
    for vox in ndindex(template_mri.shape):
        vox_ras = apply_affine(template_mri.affine, vox) - shift
        if norm(xyz - vox_ras) <= distance:
            mask[vox] = True

    return mask
