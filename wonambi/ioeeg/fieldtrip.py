from datetime import datetime
from logging import getLogger
from numpy import around, empty
from scipy.io import loadmat, savemat

from .utils import read_hdf5_chan_name
from ..utils import MissingDependency

try:
    from h5py import File
except ImportError as err:
    File = MissingDependency(err)


lg = getLogger(__name__)
VAR = 'data'


class FieldTrip:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    """
    def __init__(self, filename):
        self.filename = filename

    def return_hdr(self):
        """Return the header for further use.

        Returns
        -------
        subj_id : str
            subject identification code
        start_time : datetime
            start time of the dataset
        s_freq : float
            sampling frequency
        chan_name : list of str
            list of all the channels
        n_samples : int
            number of samples in the dataset
        orig : dict
            additional information taken directly from the header

        Notes
        -----
        It only reads hdf5 matlab files and the VARiable needs to be called
        'data'

        h5py is necessary for this function
        """
        # fieldtrip does not have this information
        orig = dict()
        subj_id = str()
        start_time = datetime.fromordinal(1)  # fake

        try:
            ft_data = loadmat(self.filename, struct_as_record=True,
                              squeeze_me=True)
            if VAR not in ft_data:
                raise KeyError('Save the FieldTrip variable as ''{}'''
                               ''.format(VAR))
            ft_data = ft_data[VAR]

            s_freq = ft_data['fsample'].astype('float64').item()
            n_samples = ft_data['trial'].item().shape[1]
            chan_name = list(ft_data['label'].item())

        except NotImplementedError:

            with File(self.filename) as f:

                if VAR not in f.keys():
                    raise KeyError('Save the FieldTrip variable as ''{}'''
                                   ''.format(VAR))

                s_freq = int(f[VAR]['fsample'].value.squeeze())
                chan_name = read_hdf5_chan_name(f, f[VAR]['label'])

                n_samples = int(around(f[f[VAR]['trial'][0].item()].shape[0]))

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

    def return_dat(self, chan, begsam, endsam):
        """Return the data as 2D numpy.ndarray.

        Parameters
        ----------
        chan : int or list
            index (indices) of the channels to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A 2d matrix, with dimension chan X samples

        """
        TRL = 0
        try:
            ft_data = loadmat(self.filename, struct_as_record=True,
                              squeeze_me=True)
            ft_data = ft_data[VAR]

            data = ft_data['trial'].item(TRL)

        except NotImplementedError:
            from h5py import File

            with File(self.filename) as f:
                data = f[f[VAR]['trial'][TRL].item()].value.T

        return data[chan, begsam:endsam]

    def return_markers(self):
        """Return all the markers (also called triggers or events).

        Returns
        -------
        list of dict
            where each dict contains 'name' as str, 'start' and 'end' as float
            in seconds from the start of the recordings, and 'chan' as list of
            str with the channels involved (if not of relevance, it's None).

        TODO
        ----
        How to read markers / events from fieldtrip file
        """
        return []


def write_fieldtrip(data, filename):
    """Export data to FieldTrip.

    Parameters
    ----------
    data : instance of ChanTime
        data with only one trial
    filename : path to file
        file to export to (include '.mat')

    Notes
    -----
    It saves mat file using Version 6 ('-v7') because it relies on scipy.io
    functions. Therefore it cannot store data larger than 2 GB.
    """
    n_trl = data.number_of('trial')
    trial = empty(n_trl, dtype='O')
    time = empty(n_trl, dtype='O')

    for trl in range(n_trl):
        trial[trl] = data.data[trl]
        time[trl] = data.axis['time'][trl]

    ft_data = {'fsample': float(data.s_freq),
               'label': data.axis['chan'][0].astype('O'),
               'trial': trial,
               'time': time,
               'cfg': 'Converted from wonambi on ' + str(datetime.now()),
               }

    savemat(filename, {VAR: ft_data})
