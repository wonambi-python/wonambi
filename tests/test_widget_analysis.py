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
                                 '_freq.csv')    
    with open(freq_path) as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    assert approx(float(rows[1][44])) == 0.0186294464902
    assert approx(float(rows[3][16])) == -4.28072153938
    
    band_path = EXPORTED_PATH / (splitext(basename(analysis_export_path))[0] + 
                                 '_band.csv')    
    with open(band_path) as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    assert approx(float(rows[1][10])) == 0.019888064040867178
    assert approx(float(rows[11][11])) == 0.008681717779629288


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
                                  '_fooof.csv')    
    with open(fooof_path) as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    assert approx(float(rows[10][1])) == 12.613759924714094
    assert approx(float(rows[10][2])) == 0.24356640365481338


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
