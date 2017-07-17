Phypno
======
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

    pip install phypno

See `Installation for details <http://phypno.readthedocs.io/installation.html>`_

If you want to scroll recordings and do some sleep scoring (requires PyQt5)

    scroll_data

Documentation
-------------
See `Documentation <http://phypno.readthedocs.io>`_

Change Log
----------
See `Change Log <http://phypno.readthedocs.io/changelog.html>`_

Requirements
------------
- Python 3.6
- numpy
- scipy
- (optional for sleep scoring GUI) PyQt5

Status
------
.. image:: https://travis-ci.org/gpiantoni/phypno.svg?branch=master
    :target: https://travis-ci.org/gpiantoni/phypno

License
-------
The project is licensed under the GPLv3 license.
Other licenses available upon request.
