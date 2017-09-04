from wonambi.attr import Surf
from wonambi.source import Morph

from .paths import surf_path


def test_source_morph():
    surf = Surf(surf_path)
    Morph(from_surf=surf)
