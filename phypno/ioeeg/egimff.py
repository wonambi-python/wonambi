
from struct import unpack


version = unpack('<I', x[:4])[0]
hdr_size = unpack('<I', x[4:8])[0]
data_size = unpack('<I', x[8:12])[0]
n_signals = unpack('<I', x[12:16])[0]

offset = []
for j in range(n_signals):
    i0 = j * 4 + 16
    i1 = i0 + 4
    offset.append(unpack('<I', x[i0:i1])[0])

i = n_signals * 4 + 16

depth = []
freq = []
for j in range(n_signals):
    i0 = j * 4 + i
    i1 = i0 + 1
    i2 = i0 + 4
    depth.append(unpack('<B', x[i0:i1])[0])
    freq.append(unpack('<I', x[i1:i2] + b'\x00')[0])

i = 2 * n_signals * 4 + 16
opt_hdr_size = unpack('<I', x[i:i + 4])[0]
i += 4
opt_hdr_type = unpack('<I', x[i:i + 4])[0]
if opt_hdr_type == 1:
    i += 4
    n_blocks = unpack('<Q', x[i:i + 8])[0]
    i += 8
    n_smp = unpack('<Q', x[i:i + 8])[0]
    i += 8
    n_signals_opt = unpack('<I', x[i:i + 4])[0]
    i += 4



unpack('<' + 'i' * 20, x[hdr_size:hdr_size + 4 * 20])





class EgiMff:
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

        """
        subj_id = str()
        start_time = datetime.datetime
        s_freq = int()
        chan_name = ['', '']
        n_samples = int()
        orig = dict()

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
        data = rand(10, 100)
        return data[chan, begsam:endsam]
