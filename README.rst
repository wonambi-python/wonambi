WONAMBI
=======
Package for the analysis of EEG, ECoG and other electrophysiology modalities.
Allows for visualization of the data and sleep stage scoring in a GUI.
Provides automatic detectors for spindles and slow waves.

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
  - SystemPlus Micromed (.trc)
  - Moberg ("EEG,Composite,SampleSeries,Composite,MRIAmp,data")
  - openephys (.continuous, .openephys)
  - BIDS-formatted data file

- Interface for Sleep Scoring

- Computes frequency analysis (spectrogram), time-frequency analysis (short-time spectrogram, Morlet wavelet)

- Detection of spindles and slow waves

- Pure Python

Installation
------------
Install wonambi by running:

    pip3 install wonambi

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
- Python 3.6 or later
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
.. image:: https://travis-ci.com/wonambi-python/wonambi.svg?branch=master
    :target: https://travis-ci.com/wonambi-python/wonambi

.. image:: https://codecov.io/gh/wonambi-python/wonambi/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/wonambi-python/wonambi

License
-------
The project is licensed under the 3-clause BSD license.
