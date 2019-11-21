Get Started
===========

Read dataset
------------
You can open your data with:

.. code-block:: python

   from wonambi import Dataset
   d = Dataset('/path/to/data')
   markers = d.read_markers()  # it reads the nev file if present

Read data
---------
You can choose to open only a segment of your data:

.. code-block:: python

   data = d.read_data(begtime=10, endtime=30)

Compute the Power Spectrum
--------------------------
You can compute the power spectrum with these commands:

.. code-block:: python

   freq = frequency(data, scaling='power')

For a more in-depth discussion of this topic, see :doc:`spectrum`.
