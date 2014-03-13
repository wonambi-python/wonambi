"""Packages containing all the possible attributes to recordings, such as
    - channels (module "chan") with class:
        - Chan
    - anatomical info (module "anat") with class:
        - Surf

Possibly include forward and inverse models.

"""
from .chan import Channels
from .anat import Surf, Freesurfer
from .scores import Scores
