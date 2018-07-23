from wonambi.scroll_data import MainWindow
from PyQt5.QtWidgets import QAction
from os.path import basename, splitext
import csv
from pytest import approx

from .test_scroll_data import (channel_make_group,
                               find_in_qt,
                               screenshot,
                               )

from .paths import (annot_psg_path,
                    gui_file,
                    GUI_PATH,
                    analysis_export_path,
                    EXPORTED_PATH,
                    )

def test_widget_analysis_frequency(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.notes.update_notes(annot_psg_path)

    w.notes.action['analyze']
    ad = w.analysis_dialog
    ad.update_evt_types()
    ad.update_groups()
    ad.grab().save(str(GUI_PATH / 'analysis_01_dialog.png'))
    ad.tab_evt.grab().save(str(GUI_PATH / 'analysis_03_event.png'))

    ad.filename = analysis_export_path
    ad.chunk['epoch'].setChecked(True)
    ad.lock_to_staging.set_value(True)
    ad.idx_chan.setCurrentRow(0)
    ad.idx_stage.setCurrentRow(2)
    ad.trans['diff'].set_value(True)
    freq = ad.frequency
    freq['export_full'].set_value(True)
    freq['export_band'].set_value(True)
    freq['band'].set_value('[[0.5-4],[4-8],[10-16],[30-50]]')
    freq['prep'].set_value(True)
    freq['norm'].set_value('by integral of each segment')
    ad.tab_freq.grab().save(str(GUI_PATH / 'analysis_02_freq.png'))
    assert ad.nseg == 127

    ad.button_clicked(ad.idx_ok)
    freq_path = EXPORTED_PATH / (splitext(basename(analysis_export_path))[0] +
                                 '_freq_full.csv')
    with open(freq_path) as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    assert approx(float(rows[1][44])) == 0.9501017730604996
    assert approx(float(rows[3][16])) == -0.348895908193285

    band_path = EXPORTED_PATH / (splitext(basename(analysis_export_path))[0] +
                                 '_freq_band.csv')
    with open(band_path) as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    assert approx(float(rows[1][10])) ==  4.81846003248371
    assert approx(float(rows[11][11])) == 3.230796520373666


def test_widget_analysis_fooof(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.notes.update_notes(annot_psg_path)

    w.notes.action['analyze']
    ad = w.analysis_dialog
    ad.update_evt_types()
    ad.update_groups()

    ad.filename = analysis_export_path
    ad.chunk['segment'].setChecked(True)
    ad.idx_chan.setCurrentRow(0)
    ad.idx_stage.setCurrentRow(1)
    freq = ad.frequency
    freq['fooof_on'].set_value(True)
    freq['prep'].set_value(False)
    freq['step'].set_value(True)
    freq['step_val'].set_value(0.5)
    freq['norm'].set_value('none')
    assert ad.nseg == 33

    ad.button_clicked(ad.idx_ok)
    fooof_path = EXPORTED_PATH / (splitext(basename(analysis_export_path))[0] +
                                  '_freq_fooof.csv')
    with open(fooof_path) as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    assert approx(float(rows[10][1])) == 12.613759924714094
    assert approx(float(rows[10][2])) == 0.24356640365481338


def test_widget_analysis_event(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.notes.update_notes(annot_psg_path)    
    w.traces.go_to_epoch(test_text_str='23:34:45')
    
    w.notes.delete_eventtype(test_type_str='spindle')    
    w.notes.new_eventtype(test_type_str='spindle')
    w.notes.action['new_event'].setChecked(True)
    w.notes.add_event('spindle', (24293.01, 24294.65), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('spindle', (24288.01, 24288.90), 'EEG Fpz-Cz (scalp)')
    w.notes.add_event('spindle', (24290.5, 24291.00), 'EEG Fpz-Cz (scalp)')

    w.notes.action['analyze']
    ad = w.analysis_dialog
    ad.update_evt_types()
    ad.update_groups()

    ad.filename = analysis_export_path
    ad.chunk['event'].setChecked(True)
    ad.idx_evt_type.setCurrentRow(1)
    ad.idx_chan.setCurrentRow(0)
    evt = ad.event
    evt['global']['count'].set_value(True)
    evt['global']['density'].set_value(True)
    evt['f1'].set_value(10)
    evt['f2'].set_value(16)
    evt['global']['all_local'].set_value(True)
    evt['sw']['avg_slope'].set_value(True)
    evt['sw']['max_slope'].set_value(True)
    ad.check_all_local()
    
    ad.button_clicked(ad.idx_ok)
    w.notes.delete_eventtype(test_type_str='spindle')
    w.close()
    
    evt_path = EXPORTED_PATH / (splitext(basename(analysis_export_path))[0] +
                                 '_params.csv')
    with open(evt_path) as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    assert approx(float(rows[0][1])) == 2
    assert approx(float(rows[1][1])) == 0.0020768431983
    assert approx(float(rows[3][15])) == 9.81616222270557
    assert approx(float(rows[8][13])) ==  8.02638098366877  


def test_widget_notes_export_csv(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    w.notes.update_notes(annot_psg_path)

    menubar = w.menuBar()

    act_annot = find_in_qt(menubar, QAction, 'Annotations')
    menubar.setActiveAction(act_annot)
    act_annot.menu().setActiveAction(w.notes.action['export_sleepstats'])

    screenshot(w, 'analysis_02_statistics.png')
    w.close()
