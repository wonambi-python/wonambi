"""Packages containing all the possible attributes to recordings, such as
    - channels (module "chan") with class:
        - Chan
    - anatomical info (module "anat") with class:
        - Surf
    - annotations and sleep scores (module "annotations") with class:
        - Annotations

Possibly include forward and inverse models.

These attributes are only "attached" to the DataType, there should not be any
consistency check when you load them. The risk is that attributes do not refer
to the correct datatype, but the advantage is that we cannot keep track of all
the possible inconsistencies (f.e. if the channel names are not the same
between the actual channels and those stored in the Channels class).

In addition, these classes are often used in isolation, even without a dataset,
so do not assume that any of the classes in the module can call the main
dataset. In other words, these classes shouldn't have methods calling the
datatype, but there can be functions in the modules that use both the
dataset and the classes below.

"""
from .chan import Channels
from .anat import Brain, Surf, Freesurfer
from .annotations import Annotations, create_empty_annotations
