Plot 3D images
==============

You can plot surfaces from freesurfer:

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 12-15

.. image:: images/viz3_01_surf.png

and you can plot the color for the whole surface:

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 23-26

.. image:: images/viz3_02_surf_color.png

or you can give the value for each vertex.
You can specify the min and max limits with ``limits_c``.

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 34-37

.. image:: images/viz3_03_surf_values.png

You can add a colorbar at the back of the head (you might need to zoom out to see it):

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 45-48

.. image:: images/viz3_04_surf_colorbar.png

You can then add channel positions, such ECoG on the surface:

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 56-61

.. image:: images/viz3_05_surf_chan.png

.. NOTE::
   Note how the channel groups had different colors.
   This is based on the channel labels.

You can also specify one color (in RGB, values between 0 and 1) to use the same color for all the channels:

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 69-74

.. image:: images/viz3_06_surf_chan_color_one.png

To specify the transparency, enter the keyword ``alpha`` (0: transparent, 1: opaque).

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 82-87

.. image:: images/viz3_07_surf_chan_color_one_alpha.png

You can also specify the color for each channel (in this example, we alternate red and blue channels).

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 95-104

.. image:: images/viz3_08_surf_chan_color_everyother.png

Finally, you can specify the values for each channels (and add a colorbar).

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 112-119

.. image:: images/viz3_09_surf_chan_values.png
