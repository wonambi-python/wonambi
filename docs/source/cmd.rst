Command Line
============
When you install **wonambi**, you'll have access to some functions in your command line.

wonambi
-------
This is the main command to run the graphical user interface (GUI).

.. code-block:: bash

   usage: wonambi [-h] [-v] [-l LOG] [--reset] [--bids]
                  [dataset] [annot] [montage]

   Package to analyze EEG, ECoG and other electrophysiology formats. It allows
   for visualization of the results and for a GUI that can be used to score sleep
   stages.

   positional arguments:
     dataset            full path to dataset to open
     annot              full path to annotations file to open
     montage            full path to montage file to open

   optional arguments:
     -h, --help         show this help message and exit
     -v, --version      Return version
     -l LOG, --log LOG  Logging level: info (default), debug
     --reset            Reset (clear) configuration file
     --bids             Read the information stored in the BIDS format


won_convert
-----------
This command allows you to convert the data from one format known to **wonambi** into another common format (like `edf`, Brain Vision, BIDS).

.. code-block:: bash

   usage: won_convert [-h] [-v] [-l LOG] [-f SAMPLING_FREQ] [-b BEGTIME]
                      [-e ENDTIME]
                      [infile] [outfile]

   Convert data from one known format to another format

   positional arguments:
     infile                full path to dataset to convert
     outfile               full path of the output file with extension (.edf)

   optional arguments:
     -h, --help            show this help message and exit
     -v, --version         Return version
     -l LOG, --log LOG     Logging level: info (default), debug
     -f SAMPLING_FREQ, --sampling_freq SAMPLING_FREQ
                           resample to this frequency (in Hz)
     -b BEGTIME, --begtime BEGTIME
                           start time in seconds from the beginning of the
                           recordings
     -e ENDTIME, --endtime ENDTIME
                           end time in seconds from the beginning of the
                           recordings
