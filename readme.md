# PHYPNO
Package to analysis EEG, ECoG and other electrophysiology formats.
It allows for visualization of the results and for a GUI that can be used to score sleep stages.

# Installation
Make sure to have `numpy` installed because it's impossible to have it as dependency in `setup.py`.
You can install it 

# Dependencies
## Required
Numpy
(not specified in setup.py because `numpy` does not like to be installed as dependency, see  [this bug](https://github.com/numpy/numpy/issues/2434))

## Optional
You can install other depene
scipy (to filter recordings, frequency analysis, read matlab files)

pyqt4 (for graphical user interface)

pyqtgraph (for visualization)

nibabel (to read freesurfer surfaces)

mne (a.k.a. mne-tools, to write MNE fiff files and multitapers, note that `mne` might require `nose` but it's not specified as required dependency)
