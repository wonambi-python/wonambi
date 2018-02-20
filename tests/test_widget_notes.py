from PyQt5.QtWidgets import (QAction,
                             QComboBox,
                             QToolBar,
                             QToolButton,
                             )
from PyQt5.QtCore import QEvent, QPointF
from PyQt5.Qt import QMouseEvent, Qt

from wonambi.scroll_data import MainWindow
from wonambi.trans.reject import remove_artf_evts

from .test_scroll_data import (channel_make_group,
                               find_in_qt,
                               find_in_qt_by_idx,
                               screenshot,
                               )

from .paths import (annot_fasst_path,
                    annot_fasst_export_file,
                    annot_psg_path,
                    gui_file,
                    GUI_PATH,
                    )


def test_widget_notes_load(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)

    toolbar = w.findChild(QToolBar, 'File Management')
    button_save = find_in_qt(toolbar, QToolButton, "Load Annotations")
    button_save.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'notes_03_load.png'))
    button_save.setStyleSheet("")


def test_widget_notes_import_fasst(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    menubar = w.menuBar()

    act_annot = find_in_qt(menubar, QAction, 'Annotations')
    menubar.setActiveAction(act_annot)

    act_import = find_in_qt(act_annot.menu(), QAction, 'Import staging')
    act_annot.menu().setActiveAction(act_import)

    act_import.menu().setActiveAction(w.notes.action['import_fasst'])

    screenshot(w, 'notes_04_import_fasst.png')
    w.close()


def test_widget_notes_show_fasst(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.notes.import_fasst(test_fasst=str(annot_fasst_path),
                         test_annot=str(annot_fasst_export_file))
    w.grab().save(str(GUI_PATH / 'notes_05_show_imported.png'))


def test_widget_notes_toolbar(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.channels.new_group(test_name='eog')
    w.notes.update_notes(annot_psg_path)
    w.traces.Y_wider()
    w.traces.go_to_epoch(test_text_str='23:00')

    toolbar = w.findChild(QToolBar, 'Annotations')

    button_event = find_in_qt(toolbar, QToolButton, 'Event Mode')
    button_event.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'notes_07_event_mode.png'))
    button_event.setStyleSheet("")

    box_evttype = find_in_qt_by_idx(toolbar, QComboBox, 0)
    box_evttype.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'notes_08_evt_type_box.png'))
    box_evttype.setStyleSheet("")

    box_stage = find_in_qt_by_idx(toolbar, QComboBox, 1)
    box_stage.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'notes_09_stage_box.png'))
    box_stage.setStyleSheet("")

    box_qual = find_in_qt_by_idx(toolbar, QComboBox, 2)
    box_qual.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'notes_10_quality_box.png'))
    box_qual.setStyleSheet("")

    w.close()


def test_widget_notes_cycle(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.channels.new_group(test_name='eog')
    w.notes.update_notes(annot_psg_path)
    w.traces.Y_wider()
    w.traces.Y_wider()
    w.traces.go_to_epoch(test_text_str='22:28')

    menubar = w.menuBar()

    act_annot = find_in_qt(menubar, QAction, 'Annotations')
    menubar.setActiveAction(act_annot)

    act_cycle = find_in_qt(act_annot.menu(), QAction, 'Cycle')
    act_annot.menu().setActiveAction(act_cycle)

    act_cycle.menu().setActiveAction(w.notes.action['cyc_start'])

    screenshot(w, 'notes_11_set_cycle_start.png')

    w.notes.get_cycle_mrkr()

    w.overview.grab().save(str(GUI_PATH / 'notes_12_cycle_marker.png'))

    w.traces.go_to_epoch(test_text_str='23:24')
    w.notes.get_cycle_mrkr(end=True)
    w.traces.go_to_epoch(test_text_str='23:29')
    w.notes.get_cycle_mrkr()
    w.traces.go_to_epoch(test_text_str='00:43')
    w.notes.get_cycle_mrkr()
    w.traces.go_to_epoch(test_text_str='02:14:30')
    w.notes.get_cycle_mrkr(end=True)

    w.overview.grab().save(str(GUI_PATH / 'notes_13_all_cycle_markers.png'))
    w.notes.clear_cycle_mrkrs(test=True)
    w.close()


def test_widget_notes_mark_event(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.channels.new_group(test_name='eog')
    w.notes.update_notes(annot_psg_path)
    w.traces.Y_wider()
    w.traces.Y_wider()
    w.traces.action['cross_chan_mrk'].setChecked(True)
    w.traces.go_to_epoch(test_text_str='23:34:45')

    w.notes.new_eventtype(test_type_str='spindle')
    w.notes.action['new_event'].setChecked(True)
    w.notes.add_event('spindle', (24293.01, 24294.65), 'EEG Pz-Oz (scalp)')

    screenshot(w, 'notes_14_mark_event.png')

    w.notes.add_event('spindle', (24288.01, 24288.90), 'EEG Fpz-Cz (scalp)')
    w.notes.add_event('spindle', (24297.5, 24298.00), 'EEG Fpz-Cz (scalp)')

    screenshot(w, 'notes_20_mark_short_event.png')

    pos = w.traces.mapFromScene(QPointF(24294, 75))
    mouseclick = QMouseEvent(QEvent.MouseButtonPress, pos,
                             Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    w.traces.mousePressEvent(mouseclick)

    screenshot(w, 'notes_15_highlight_event.png')

    w.notes.delete_eventtype(test_type_str='spindle')
    w.close()


def test_widget_notes_dialogs(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.notes.update_notes(annot_psg_path)

    w.notes.action['spindle']
    spd = w.spindle_dialog
    spd.grab().save(str(GUI_PATH / 'notes_16_spindledialog.png'))

    spd.button_clicked(spd.idx_cancel)

    w.notes.action['slow_wave']
    swd = w.slow_wave_dialog
    swd.grab().save(str(GUI_PATH / 'notes_17_slowwavedialog.png'))

    swd.button_clicked(swd.idx_cancel)

    w.notes.action['analyze_events']
    ead = w.event_analysis_dialog
    ead.grab().save(str(GUI_PATH / 'notes_18_eventanalysisdialog.png'))

    ead.button_clicked(ead.idx_cancel)

    w.notes.action['merge_events']
    md = w.merge_dialog
    md.grab().save(str(GUI_PATH / 'notes_19_mergedialog.png'))

    md.button_clicked(md.idx_cancel)


def test_widget_notes_export_csv(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    menubar = w.menuBar()

    act_annot = find_in_qt(menubar, QAction, 'Annotations')
    menubar.setActiveAction(act_annot)
    act_annot.menu().setActiveAction(w.notes.action['export'])

    screenshot(w, 'notes_06_export.png')
    w.close()


def test_widget_notes_import_error(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.notes.import_fasst(test_fasst=str(gui_file),
                         test_annot=str(annot_fasst_export_file))
    assert 'FASST .mat file' in w.statusBar().currentMessage()

def test_widget_notes_remove_artf_evts(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.channels.new_group(test_name='eog')
    w.notes.update_notes(annot_psg_path)

    w.notes.new_eventtype(test_type_str='Artefact')
    w.notes.action['new_event'].setChecked(True)
    w.notes.add_event('Artefact', (1, 2), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (3, 6), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (7, 10), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (14, 31), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (70, 85), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (87, 90), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (90, 92), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (105, 120), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (125.0, 125.2), 'EEG Pz-Oz (scalp)')
    w.notes.add_event('Artefact', (132, 142), 'EEG Pz-Oz (scalp)')

    times = [(8,15), (30,50), (56, 100), (100, 111), (135, 140), (150, 160)]
    new_times = remove_artf_evts(times, w.notes.annot)

    assert new_times == [(10, 14), (31, 50), (56, 70), (85, 87), (92, 100),
                         (100, 105), (150, 160)]

    w.notes.delete_eventtype(test_type_str='Artefact')
    w.close()
