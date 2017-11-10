Change Log
==========
Version 4
----------
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
- **1.00**: phypno / sleeptimes -> wonambi
