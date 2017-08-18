WONAMBI
=======
Package to analysis EEG, ECoG and other electrophysiology formats.
It allows for visualization of the results and for a GUI that can be used to score sleep stages.

Features
--------
- Reader and writer for EDF, EGI MFF, Fieldtrip, FIFF file formats
- Interface for Sleep Scoring
- Computes frequency analysis (spectrogram), time-frequency analysis (Morlet wavelet)
- Pure Python

Installation
------------
Install phypno by running:

    pip install wonambi

See `Installation for details <http://gpiantoni.github.io/phypno/installation.html>`_

If you want to scroll recordings and do some sleep scoring (requires PyQt5)

    wonambi

Documentation
-------------
See `Documentation <http://gpiantoni.github.io/phypno>`_

Change Log
----------
See `Change Log <http://gpiantoni.github.io/phypno/changelog.html>`_

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
.. image:: https://travis-ci.org/gpiantoni/phypno.svg?branch=master
    :target: https://travis-ci.org/gpiantoni/phypno

.. image:: https://codecov.io/gh/gpiantoni/phypno/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/gpiantoni/phypno

License
-------
The project is licensed under the GPLv3 license.
Other licenses available upon request.
