from datetime import datetime
from pytest import raises
from PyQt5.QtWidgets import (QAction,
                             QApplication,
                             )
from PyQt5.QtCore import QTimer
from time import sleep

from wonambi.scroll_data import MainWindow
from wonambi.widgets.traces import _convert_timestr_to_seconds

from .test_scroll_data import find_in_qt, channel_make_group
from .paths import gui_file, GUI_PATH


def test_widget_traces_gotoepoch(qtbot):

    w = MainWindow()
    w.show()
    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()

    menubar = w.menuBar()

    act_navigation = find_in_qt(menubar, QAction, 'Navigation')
    menubar.setActiveAction(act_navigation)
    act_navigation.menu().setActiveAction(w.traces.action['go_to_epoch'])

    # --- Complex code to capture screenshot of menubar ---#
    def screenshot():
        screen = QApplication.primaryScreen()
        png_name = str(GUI_PATH / 'traces_01_gotoepoch.png')
        screen.grabWindow(0, w.x(), w.y(), w.width(), w.height()).save(png_name)

    # lots of processEvents needed
    QApplication.processEvents()
    QTimer.singleShot(3000, screenshot)
    QApplication.processEvents()
    sleep(5)
    QApplication.processEvents()
    w.close()
    # --- ---#

    w.traces.go_to_epoch(test_text_str='xxx')
    assert w.statusBar().currentMessage() == 'Input can only contain digits and colons'

    w.traces.go_to_epoch(test_text_str='1130')
    assert w.value('window_start') == 1130

    w.traces.go_to_epoch(test_text_str='22:30')
    assert w.value('window_start') == 20400

    w.info.idx_start.setStyleSheet("background-color: red;")
    w.info.grab().save(str(GUI_PATH / 'traces_02_gotoepoch.png'))
    w.info.idx_start.setStyleSheet("")


def test_convert_timestr():
    orig_start_time = datetime(2010, 10, 10, 20)
    assert _convert_timestr_to_seconds('444', orig_start_time) == 444
    assert _convert_timestr_to_seconds('-444', orig_start_time) == -444
    assert _convert_timestr_to_seconds('22:30', orig_start_time) == 9000
    assert _convert_timestr_to_seconds('2:30:10', orig_start_time) == 23410

    with raises(ValueError):
        _convert_timestr_to_seconds('xxx', orig_start_time)

    with raises(ValueError):
        _convert_timestr_to_seconds('23:90', orig_start_time)
