from PyQt5.QtWidgets import (QAction,
                             QToolBar,
                             QToolButton,
                             QApplication,
                             )

from PyQt5.QtCore import QTimer
from time import sleep
from wonambi.scroll_data import MainWindow

from .test_scroll_data import find_in_qt

from .paths import (annot_fasst_path,
                    annot_fasst_export_file,
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

    # --- Complex code to capture screenshot of menubar ---#
    def screenshot():
        screen = QApplication.primaryScreen()
        png_name = str(GUI_PATH / 'notes_04_import_fasst.png')
        screen.grabWindow(0, w.x(), w.y(), w.width(), w.height()).save(png_name)

    # lots of processEvents needed
    QApplication.processEvents()
    QTimer.singleShot(3000, screenshot)
    QApplication.processEvents()
    sleep(5)
    QApplication.processEvents()
    w.close()
    # --- ---#


def test_widget_notes_show_fasst(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.notes.import_fasst(test_fasst=str(annot_fasst_path),
                         test_annot=str(annot_fasst_export_file))
    w.grab().save(str(GUI_PATH / 'notes_05_show_imported.png'))


def test_widget_notes_import_error(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.notes.import_fasst(test_fasst=str(gui_file),
                         test_annot=str(annot_fasst_export_file))
    assert 'FASST .mat file' in w.statusBar().currentMessage()
