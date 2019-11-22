WONAMBI
=======
Package to analysis EEG, ECoG and other electrophysiology formats.
It allows for visualization of the results and for a GUI that can be used to score sleep stages.

Features
--------
- Can read files of format:

  - Axon (.abf, ABF2 only)
  - BCI2000 (.dat)
  - Blackrock (.nev, .ns2, .ns3, .ns5)
  - Brain Vision (.vhdr, .vmrk, .eeg / .dat)
  - EEGLAB (.set, .set / .fdt)
  - European Data Format (.edf)
  - EGI MFF (.mff)
  - Fieldtrip (.mat)
  - mne FIFF (.fiff)
  - Moberg ("EEG,Composite,SampleSeries,Composite,MRIAmp,data")
  - openephys (.continuous, .openephys)

- Interface for Sleep Scoring

- Computes frequency analysis (spectrogram), time-frequency analysis (short-time spectrogram, Morlet wavelet)

- Detection of spindles and slow waves

- Pure Python

Installation
------------
Install wonambi by running:

    pip install wonambi

See `Installation for details <http://wonambi-python.github.io/installation.html>`_

If you want to scroll recordings and do some sleep scoring (requires PyQt5)

    wonambi

Run it!
-------
From the command line, simply type:

    wonambi

To open a dataset directly, add the full path to the file you want to open:

    wonambi /home/me/sleep_recordings.edf

Documentation
-------------
See `Documentation <http://wonambi-python.github.io/>`_

Change Log
----------
See `Change Log <http://wonambi-python.github.io/changelog.html>`_

Requirements
------------
- Python 3.6
- numpy
- scipy

Optional Requirements
---------------------
- PyQt5 (optional for sleep scoring GUI)
- python-vlc (optional, to watch embedded movies)
- vispy (optional to plot 3D brain surfaces and electrodes)
- h5py (optional to read FieldTrip Matlab files)
- mne (optional, to export to mne FIFF files)
- nibabel (optional to read freesurfer)
- tensorpac (optional to run phase-amplitude analysis, tensorpac version should be 0.5.6)
- fooof 1.0 (optional to run parametrization of power spectra)

Status
------
.. image:: https://travis-ci.org/wonambi-python/wonambi.svg?branch=master
    :target: https://travis-ci.org/wonambi-python/wonambi

.. image:: https://codecov.io/gh/wonambi-python/wonambi/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/wonambi-python/wonambi

License
-------
The project is licensed under the GPLv3 license.
Other licenses available upon request.
