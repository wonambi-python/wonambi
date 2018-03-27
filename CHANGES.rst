Change Log
==========
Version 5
----------
- **5.01**: Analysis Console

Version 4
----------
- **4.27**: hotfix: spindle frequency
- **4.26**: console bugfixes, almost ready; removed evt analysis dialog
- **4.25**: fix export svg
- **4.24**: analysis console event export fix; ferrarelli2007 removed for now
- **4.23**: export traces or overview to svg
- **4.22**: improved sleep stats
- **4.21**: sometimes detected events can be None
- **4.20**: handle weird / unrecognized sleep stages and mark them as unknown
- **4.19**: improved micromed reader
- **4.18**: full documentation for sleep statistics
- **4.17**: correct way to get timestamps for lights out and lights on
- **4.16**: Enter relative or absolute time for lights out and on
- **4.15**: improvements and fixes to detections; dataset export to edf and import from text
- **4.14**: SW detection fixes
- **4.13**: cycle option in detections; spindle detection fixes; sleep stats export
- **4.12**: bugfix as before
- **4.11**: bugfix of gui when pressing left and right button together
- **4.10**: clear error messages and fix reading mff
- **4.09**: improvements on analysis dialog. EDF reading more robust
- **4.08**: fixed event deletion; improved i/o
- **4.07**: updates and fixes for spindle detection
- **4.06**: new spindle method; fix for Nir2011; epoch selection ; bugfixes
- **4.05**: save and load montage when filtering is set to 0 (None)
- **4.04**: use variable epoch length for scoring, better handling of ABF2 files
- **4.03**: change nan to zero so we can at least plot something if there are missing data 
- **4.02**: you can open a dataset from the command line (and better logging)
- **4.01**: frequency analysis is much more consistent and correct

Version 3
----------
- **3.11**: fixed event marking; stage now visible when zoomed in <30s
- **3.08**: list where the settings are stored
- **3.07**: docs and tests for notes, analysis; some minor fixes
- **3.06**: use time placeholder when abf files have empty time info
- **3.05**: go to epoch gets input from user
- **3.04**: support for axon abf file format
- **3.03**: SW detection; import sleep scores for Alice, Compumedics, Domino, RemLogic, Sandman; merge events; bugfixes
- **3.02**: bugfix when opening montage
- **3.01**: merged with sleepytimes, including pretty GUI for spindle / SW detection

Version 2
----------
- **2.06**: import FASST sleep scores
- **2.05**: full coverage of plot3 and detect
- **2.04**: disable buttons in channels widget (+tests/docs)
- **2.03**: use markers for channels 3d plots
- **2.02**: new vispy surface for Viz3
- **2.01**: use setup_wonambi.py for booking, it works in appveyor

Version 1
----------
- **1.02**: test with vispy (using pip instead of conda)
- **1.01**: improved EDF reader (multiple frequencies and annotations)
- **1.00**: phypno / sleepytimes -> wonambi
