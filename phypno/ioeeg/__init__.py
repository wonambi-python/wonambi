"""Package to import and export common formats. Main classes:
  - filename: the name of the filename or directory

  - return_hdr, which returns the header

    - subj_id : str
        subject identification code
    - start_time : datetime
        start time of the dataset
    - s_freq : float
        sampling frequency
    - chan_name : list of str
        list of all the channels
    - n_samples : int
        number of samples in the dataset
    - orig : dict
        additional information taken directly from the header

  - return_dat, which returns the data as 2D np.ndarray. Parameters are:

    - chan : int or list
        index (indices) of the channels to read
    - begsam : int
        index of the first sample
    - endsam : int
        index of the last sample

Each module should have a main class depending on the file type. The only input
is the filepath (or directory path). This class needs to have two methods:

Biosig has a very large library of tools to read various formats. I think it's
best to use it in general. However, it has bindings only for Python2 and running
Makefile/swig using python3 is tricky. Use pure python for EDF, and maybe other
common format (fiff, fieldtrip, eeglab) in python3, then if necessary use
python2 as script using biosig for all the other formats.

"""
from .edf import Edf  # write_edf
from .ktlx import Ktlx  # write_ktlx
# from .fiff import Fiff, write_fiff
# from .fieldtrip import Fieldtrip, write_fieldtrip
# from .eeglab import Eeglab, write_eeglab
