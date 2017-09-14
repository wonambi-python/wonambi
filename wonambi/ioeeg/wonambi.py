"""Package to import and export common formats.
"""
from datetime import datetime, timedelta
from json import dump, load
from pathlib import Path
from numpy import c_, empty, float64, NaN, memmap


class Wonambi:
    """Class to read the data in Wonambi format, which is fast to write and read

    Parameters
    ----------
    filename : path to file
        the name of the filename with extension .won
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
            the json file
        """
        with open(self.filename, 'r') as f:
            orig = load(f)

        start_time = datetime.strptime(orig['start_time'],
                                       '%Y-%m-%d %H:%M:%S.%f')
        self.memshape = (len(orig['chan_name']),
                         orig['n_samples'])
        self.dtype = orig.get('dtype', 'float64')

        return (orig['subj_id'], start_time, orig['s_freq'], orig['chan_name'],
                orig['n_samples'], orig)

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
            A 2d matrix, with dimension chan X samples. To save memory, the
            data are memory-mapped, and you cannot change the values on disk.

        Raises
        ------
        FileNotFoundError
            if .dat file is not in the same directory, with the same name.

        Notes
        -----
        When asking for an interval outside the data boundaries, it returns NaN
        for those values. It then converts the memmap to a normal numpy array,
        I think, and so it reads the data into memory. However, I'm not 100%
        sure that this is what happens.
        """
        memmap_file = Path(self.filename).with_suffix('.dat')
        if not memmap_file.exists():
            raise FileNotFoundError('Could not find ' + str(memmap_file))

        data = memmap(str(memmap_file), self.dtype, mode='c',
                      shape=self.memshape, order='F')

        n_smp = self.memshape[1]
        dat = data[chan, max((begsam, 0)):min((endsam, n_smp))].astype(float64)

        if begsam < 0:

            pad = empty((dat.shape[0], 0 - begsam))
            pad.fill(NaN)
            dat = c_[pad, dat]

        if endsam >= n_smp:

            pad = empty((dat.shape[0], endsam - n_smp))
            pad.fill(NaN)
            dat = c_[dat, pad]

        return dat

    def return_markers(self):
        """This format doesn't have markers.

        Returns
        -------
        empty list

        Raises
        ------
        FileNotFoundError
            when it cannot read the events for some reason (don't use other
            exceptions).
        """
        return []


def write_wonambi(data, filename, subj_id='', dtype='float64'):
    """Write file in simple Wonambi format.

    Parameters
    ----------
    data : instance of ChanTime
        data with only one trial
    filename : path to file
        file to export to (the extensions .won and .dat will be added)
    subj_id : str
        subject id
    dtype : str
        numpy dtype in which you want to save the data

    Notes
    -----
    Wonambi format creates two files, one .won with the dataset info as json
    file and one .dat with the memmap recordings.

    It will happily overwrite any existing file with the same name.

    Memory-mapped matrices are column-major, Fortran-style, to be compatible
    with Matlab.
    """
    filename = Path(filename)

    json_file = filename.with_suffix('.won')
    memmap_file = filename.with_suffix('.dat')

    start_time = data.start_time + timedelta(seconds=data.axis['time'][0][0])

    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S.%f')
    dataset = {'subj_id': subj_id,
               'start_time': start_time_str,
               's_freq': data.s_freq,
               'chan_name': list(data.axis['chan'][0]),
               'n_samples': int(data.number_of('time')[0]),
               'dtype': dtype,
               }

    with json_file.open('w') as f:
        dump(dataset, f, sort_keys=True, indent=4)

    memshape = (len(dataset['chan_name']),
                dataset['n_samples'])

    mem = memmap(str(memmap_file), dtype, mode='w+', shape=memshape, order='F')
    mem[:, :] = data.data[0]
    mem.flush()  # not sure if necessary
