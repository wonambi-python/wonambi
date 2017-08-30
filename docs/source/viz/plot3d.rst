Plot 3D images
==============

You can plot surfaces from freesurfer:

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 12-15

.. image:: images/viz3_01_surf.png

You can then add channel positions, such ECoG on the surface:

.. literalinclude:: ../../../tests/test_viz_plot3d.py
   :lines: 22-27

.. image:: images/viz3_02_surf_chan.png

Note how the channel groups had different colors.

