.. raw:: html

    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

.. _powerspectrum:

Frequency Domain
================

Frequency
---------

Let's create a signal with amplitude of 1 V and a frequency of 10 Hz:

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 12-25

.. raw:: html
    :file: plotly/freq_01_data.html

We can transform it to the frequency-domain, by computing the power spectral density (default option):

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 28-42

.. raw:: html
    :file: plotly/freq_02_freq.html

Note that the Parseval's theorem holds:

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 49-51


Welch's Method
""""""""""""""

If you want to apply the Welch's method (compute PSD on 1s long, 50% overlapping windows and Hann window) use:

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 53-68

.. raw:: html
    :file: plotly/freq_03_welch.html
    
Multitapers
"""""""""""

A common approach is to use multitaper to suppress the activity outside the frequency band of interest and to smooth the frequency band of interest:

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 72-87

.. raw:: html
    :file: plotly/freq_04_dpss.html

.. NOTE::
    You can either specify the half-bandwidth smoothing in the frequency domain (``halfbandwidth``) or the normalized halfbandwidth (``NW``), where::

      NW = halfbandwidth * duration

Energy Spectral Density
"""""""""""""""""""""""

All the above examples were transformed to the Power Spectral Density (PSD).
PSD is appropriate for signals that are (roughly) periodic.
However, if your signal is limited in the time domain, it makes sense to compute the Energy Spectral Density (ESD, see `wikipedia`_ for discussion). 

So, for a signal that has a clear start and end:

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 92-107

.. raw:: html
    :file: plotly/freq_05_esd.html

You can compute the ESD in this way:

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 110-124

.. raw:: html
    :file: plotly/freq_06_esd.html

.. NOTE::
    The units for the PSD are V\ :sup:`2`\/ Hz while those for the ESD are V\ :sup:`2`\ .

The Parseval's theorem holds in this case as well, but we need to make sure to include the duration as well:

.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 128-130

Complex Output
""""""""""""""
To get the complex output (so, not the PSD or ESD), you should pass the argument ``output='complex'``.


.. literalinclude:: ../../../tests/test_trans_frequency_doc.py
    :lines: 133-148

.. raw:: html
    :file: plotly/freq_07_complex.html


.. NOTE::
    The complex frequency domain returns positive and negative frequencies.

.. NOTE::
    The complex output has an additional dimension, called ``taper``. 
    This is necessary in the case of ``taper='dpss'`` because it does not make sense to average in the complex domain over multiple tapers.
    For consistency, there is also a ``taper`` dimension also when using single tapers (such as ``hann`` or ``boxcar``).

Comparison to Scipy
"""""""""""""""""""

The code reflects quite some ideas from ``scipy``, but the nomenclature in ``scipy`` might give rise to some confusion, especially if compared to other sources (well summarized by `wikipedia`_).

+-------------------------+------------------+------------------------+------------------------------+
| Name                    | Units            | scipy parameters       | wonambi parameters           |
+=========================+==================+========================+==============================+
| Power Spectral Density  | V\ :sup:`2`\/ Hz | ``output='psd'``       | ``output='spectraldensity'`` |
|                         |                  | ``scaling='density'``  | ``scaling='power'``          |
+-------------------------+------------------+------------------------+------------------------------+
| Energy Spectral Density | V\ :sup:`2`\     | ``output='psd'``       | ``output='spectraldensity'`` |
|                         |                  | ``scaling='spectrum'`` | ``scaling='energy'``         |
+-------------------------+------------------+------------------------+------------------------------+
| Complex Fourier         | V                | ``output='complex'``   | ``output='complex'``         |
|                         |                  | ``scaling='spectrum'`` | ``scaling='energy'``         |
+-------------------------+------------------+------------------------+------------------------------+


.. _wikipedia:
    https://en.wikipedia.org/wiki/Spectral_density


Time-Frequency
--------------

There are two main approaches to the time-frequency analysis:

 - Spectrogram / short-time Fourier transform
 - Morlet wavelets

Spectrogram / STFT
""""""""""""""""""

The first approach is identical to computing ``frequency()`` on small epochs.
The duration of the epochs is defined by ``duration``, and you can specify either the ``overlap`` (between 0, no overlap, and 1, complete overlap) or the ``step`` (distance between epochs, in seconds).
The output of ``timefrequency()`` has a different name than the output of ``frequency()`` for consistency with the literature, so:

+--------------------------+------------------------------+
| timefrequency()          | frequency()                  |
+==========================+==============================+
| ``output='spectrogram'`` | ``output='spectraldensity'`` |
+--------------------------+------------------------------+
| ``output='stft'``        | ``output='complex'``         |
+--------------------------+------------------------------+

The other arguments of ``timefrequency()`` are the same as ``frequency()``.

Wavelet
"""""""

Morlet Wavelets can be used for time-frequency analysis and have an intuitive tradeoff between time and frequency resolution.
The catch is there is no straightforward way to normalize the output of the wavelets.
The Parseval's theorem does not hold because wavelets are not orthogonal.
