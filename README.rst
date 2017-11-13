WONAMBI
=======
Package to analysis EEG, ECoG and other electrophysiology formats.
It allows for visualization of the results and for a GUI that can be used to score sleep stages.

Features
--------
- Can read files of format:

  - Axon (.abf, ABF2 only)
  - Blackrock (.nev, .ns2, .ns3, .ns5)
  - BCI2000 (.dat)
  - European Data Format (.edf)
  - EGI MFF (.mff)
  - Fieldtrip (.mat)
  - mne FIFF (.fiff)

- Interface for Sleep Scoring

- Computes frequency analysis (spectrogram), time-frequency analysis (Morlet wavelet)

- Pure Python

Installation
------------
Install phypno by running:

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
- PyQt5 (optional for sleep scoring GUI)
- nibabel (optional to read freesurfer)
- mne (optional to compute multitaper)

Status
------
.. image:: https://travis-ci.org/wonambi-python/wonambi.svg?branch=master
    :target: https://travis-ci.org/wonambi-python/wonambi

.. image:: https://ci.appveyor.com/api/projects/status/arpojw273ucqbsf6/branch/master?svg=true
    :target: https://ci.appveyor.com/project/gpiantoni/wonambi

.. image:: https://codecov.io/gh/wonambi-python/wonambi/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/wonambi-python/wonambi

License
-------
The project is licensed under the GPLv3 license.
Other licenses available upon request.
