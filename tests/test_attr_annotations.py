from datetime import datetime
from pytest import raises

from wonambi import Dataset
from wonambi.attr import (Annotations,
                          create_empty_annotations,
                          )
from wonambi.attr.annotations import create_annotation
from wonambi.utils.exceptions import UnrecognizedFormat


from .paths import (annot_file,
                    annot_export_file,
                    annot_alice_path,
                    annot_compumedics_path,
                    annot_domino_path,
                    annot_fasst_export_file,
                    annot_fasst_path,
                    annot_remlogic_path,
                    annot_sandman_path,
                    annot_psg_path,
                    annot_sleepstats_path,
                    ns2_file,
                    )


def test_create_annot():
    d = Dataset(ns2_file)
    create_empty_annotations(annot_file, d)


def test_read_annot_str():
    Annotations(annot_file)


def test_read_annot_path():
    annot = Annotations(annot_file)
    annot.add_rater('test')
    annot.add_rater('test')
    annot.add_rater('test_2')

    annot.dataset
    annot.start_time
    annot.first_second
    annot.last_second
    assert len(annot.raters) == 2
    annot.remove_rater('test_2')
    assert len(annot.raters) == 1

    assert annot.current_rater == 'test'
    
    annot.set_stage_for_epoch(510, 'REM')
    
    assert annot.get_epoch_start(517) == 510
    
    assert annot.get_stage_for_epoch(510, 30) == 'REM'
    
    with raises(KeyError):
        annot.get_rater('XXX')
        
    annot.export(annot_export_file)
    
    with annot_export_file.open() as f:
        assert '18:31:14,510,540,REM' in f.read()

        
def test_bookmarks():
    d = Dataset(ns2_file)
    create_empty_annotations(annot_file, d)

    annot = Annotations(annot_file)
    
    with raises(IndexError):
        annot.current_rater
    
    with raises(IndexError):
        annot.add_bookmark('bookmark', (1, 2), ('Fpz', ))

    annot.add_rater('test')
    annot.add_bookmark('bookmark', (1, 2), ('Fpz', ))    
    assert len(annot.get_bookmarks()) == 1
    annot.remove_bookmark('bookmark')
    assert len(annot.get_bookmarks()) == 0
        

def test_events():
    d = Dataset(ns2_file)
    create_empty_annotations(annot_file, d)

    annot = Annotations(annot_file)
    with raises(IndexError):
        annot.add_event_type('spindle')

    annot.add_rater('test')
    annot.add_event_type('spindle')
    annot.add_event_type('spindle')

    assert len(annot.event_types) == 1

    annot.add_event('slowwave', (1, 2), chan=('FP1', ))
    annot.add_event('spindle', (3, 4))
    assert len(annot.event_types) == 2
    assert len(annot.get_events()) == 2

    annot.remove_event_type('spindle')
    assert len(annot.event_types) == 1
    assert len(annot.get_events()) == 1
    
    annot.remove_event('slowwave')
    assert len(annot.event_types) == 1
    assert len(annot.get_events()) == 0
    

def test_epochs():
    d = Dataset(ns2_file)
    create_empty_annotations(annot_file, d)

    annot = Annotations(annot_file)
    annot.add_rater('test')
    
    assert len(annot.get_epochs()) == 50
    assert len(annot.get_epochs(time=(1000,2000))) == 16
    

def test_get_cycles():
    d = Dataset(ns2_file)
    create_empty_annotations(annot_file, d)

    annot = Annotations(annot_file)
    annot.add_rater('test')
    
    annot.set_cycle_mrkr(510)
    annot.set_cycle_mrkr(540)
    annot.set_cycle_mrkr(570)
    annot.set_cycle_mrkr(600, end=True)
    
    cycles = annot.get_cycles()
    assert len(cycles) == 3
    assert cycles[2] == (570, 600, 3)
    
    annot.remove_cycle_mrkr(510)
    annot.clear_cycles()
    
    cycles = annot.get_cycles()
    assert cycles is None
        

def test_import_alice():
    annot = Annotations(annot_file)
    record_start = datetime(2000, 1, 1, 22, 55, 6)
    annot.import_staging(str(annot_alice_path), 'alice', 'alice', record_start)
    assert annot.time_in_stage('REM') == 5160


def test_import_compumedics():
    annot = Annotations(annot_file)
    record_start = datetime(2000, 1, 1, 0, 0, 0)
    annot.import_staging(str(annot_compumedics_path), 'compumedics', 
                         'compumedics', record_start, 
                         staging_start=record_start)
    assert annot.time_in_stage('REM') == 5970


def test_import_domino():
    annot = Annotations(annot_file)
    record_start = datetime(2015, 9, 21, 21, 40, 30)
    annot.import_staging(str(annot_domino_path), 'domino', 'domino', 
                         record_start)
    assert annot.time_in_stage('REM') == 2460


def test_import_remlogic():
    annot = Annotations(annot_file)
    record_start = datetime(2016, 8, 9, 22, 21, 30)
    annot.import_staging(str(annot_remlogic_path), 'remlogic', 'remlogic', 
                         record_start)
    assert annot.time_in_stage('REM') == 3420


def test_import_sandman():
    annot = Annotations(annot_file)
    record_start = datetime(2010, 10, 10, 21, 3, 36)
    annot.import_staging(str(annot_sandman_path), 'sandman', 'sandman', 
                         record_start)
    assert annot.time_in_stage('REM') == 5610


def test_import_fasst():
    annot = create_annotation(annot_fasst_export_file,
                              from_fasst=annot_fasst_path)
    assert annot.time_in_stage('NREM3') == 2970


def test_import_fasst_error():
    with raises(UnrecognizedFormat):
        create_annotation(annot_fasst_export_file,
                          from_fasst=ns2_file)
        

def test_export_sleepstats():
    annot = Annotations(annot_psg_path)
    assert annot.export_sleep_stats(annot_sleepstats_path, 0, 29000) == (338, 
                                   36, 327)
