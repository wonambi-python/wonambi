from datetime import datetime
from pytest import raises

from wonambi import Dataset
from wonambi.attr import (Annotations,
                          create_empty_annotations,
                          )
from wonambi.attr.annotations import create_annotation
from wonambi.utils.exceptions import UnrecognizedFormat


from .paths import (annot_file,
                    annot_domino_path,
                    annot_fasst_path,
                    annot_fasst_export_file,
                    ns2_file,
                    )


def test_create_annot():
    d = Dataset(ns2_file)
    create_empty_annotations(annot_file, d)


def test_read_annot_str():
    Annotations(annot_file)


def test_read_annot_path():
    annot = Annotations(annot_file)
    annot.add_rater('text')
    annot.add_rater('text')
    annot.add_rater('text_2')

    annot.dataset
    annot.start_time
    annot.first_second
    annot.last_second
    assert len(annot.raters) == 2
    annot.remove_rater('text_2')
    assert len(annot.raters) == 1

    assert annot.current_rater == 'text'


def test_import_domino():
    annot = Annotations(annot_file)
    record_start = datetime(2015, 9, 21, 21, 40, 30)
    annot.import_domino(str(annot_domino_path), 'domino', record_start)
    assert annot.time_in_stage('REM') == 2460


def test_import_fasst():
    annot = create_annotation(annot_fasst_export_file,
                              from_fasst=annot_fasst_path)
    assert annot.time_in_stage('NREM3') == 2970


def test_import_fasst_error():
    with raises(UnrecognizedFormat):
        create_annotation(annot_fasst_export_file,
                          from_fasst=ns2_file)
