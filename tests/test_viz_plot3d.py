from wonambi.viz import Viz3
from wonambi.attr import Surf, Channels

from .utils import VIZ_PATH, ANNOT_PATH
from .test_attr_anat import surf_path


annot = ANNOT_PATH / 'bert_chan_locs.csv'

def test_widget_labels(qtbot):

    surf = Surf(surf_path)

    v = Viz3()
    v.add_surf(surf)
    v.save(VIZ_PATH / 'viz3_01_surf.png')
    
    channels = Channels(annot)
