from PyQt5.QtWidgets import (QAction,
                             QComboBox,
                             QToolBar,
                             QToolButton,
                             )

from wonambi.scroll_data import MainWindow

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


def test_widget_notes_toolbar(qtbot):
    
    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.channels.new_group(test_name='eog')
    w.notes.update_notes(annot_psg_path)
    w.traces.go_to_epoch(test_text_str='23:00')
    w.traces.Y_wider()
    
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
