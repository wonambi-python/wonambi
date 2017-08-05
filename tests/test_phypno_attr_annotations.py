from phypno.attr import Annotations

from .utils import SAMPLE_PATH

annot_file = SAMPLE_PATH / 'annot' / 'blackrock_scores.xml'


def test_read_annot_str():
    Annotations(annot_file)


def test_read_annot_path():
    annot = Annotations(annot_file)
