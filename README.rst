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

See `Installation for details <http://wonambi-python.github.io/installation.html>`_

If you want to scroll recordings and do some sleep scoring (requires PyQt5)

    wonambi

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
