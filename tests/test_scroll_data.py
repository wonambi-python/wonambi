from PyQt5.QtWidgets import (QDockWidget,
                             QPushButton,
                             QApplication,
                             )

from PyQt5.QtCore import QTimer
from time import sleep

from wonambi.scroll_data import MainWindow

from .paths import (gui_file,
                    GUI_PATH,
                    )


def test_scroll_data(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.grab().save(str(GUI_PATH / 'open_01_start.png'))

    w.info.idx_filename.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'open_02_open_dataset.png'))
    w.info.idx_filename.setStyleSheet("")

    w.info.open_dataset(str(gui_file))

    new_button = w.channels.layout().itemAt(0).itemAt(0).widget()
    new_button.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'open_03_loaded.png'))
    new_button.setStyleSheet("")

    channel_make_group(w, png=True)

    # this shows selected channels and the apply button
    button_apply = find_in_qt(w.channels, QPushButton, 'Apply')
    button_apply.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'open_05_chan.png'))
    button_apply.setStyleSheet("")

    button_apply.click()
    w.grab().save(str(GUI_PATH / 'open_06_traces.png'))


# --- Util functions --- #
def channel_make_group(w, png=False):
    dockwidget_chan = w.findChild(QDockWidget, 'Channels')
    dockwidget_chan.raise_()

    w.channels.new_group(test_name='scalp')

    if png:
        w.grab().save(str(GUI_PATH / 'open_04_channel_new.png'))

    chan_tab_i = w.channels.tabs.currentIndex()
    channelsgroup = w.channels.tabs.widget(chan_tab_i)
    channelsgroup.idx_l0.item(0).setSelected(True)
    channelsgroup.idx_l0.item(1).setSelected(True)
    channelsgroup.idx_l0.item(2).setSelected(True)


def find_in_qt(w, qtype, text):
    # workaround, because qt cannot find the text sometimes
    all_child = w.findChildren(qtype)
    buttons = [ch for ch in all_child if ch.text() == text]
    if buttons:
        return buttons[0]


def find_in_qt_by_idx(w, qtype, idx):
    # in some cases, there is no name associated with the child
    all_child = w.findChildren(qtype)
    if idx >= len(all_child):
        return
    
    return all_child[idx]


def screenshot(w, png):
    """Complex code to capture screenshot of menubar
    """
    def screenshot_in_qt():
        screen = QApplication.primaryScreen()
        png_name = str(GUI_PATH / png)
        screen.grabWindow(0, w.x(), w.y(), w.width(), w.height()).save(png_name)

    # lots of processEvents needed
    QApplication.processEvents()
    QTimer.singleShot(3000, screenshot_in_qt)
    QApplication.processEvents()
    sleep(5)
    QApplication.processEvents()
