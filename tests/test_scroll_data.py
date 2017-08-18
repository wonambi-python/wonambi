from phypno.scroll_data import MainWindow

from .test_phypno_ioeeg_bci2000 import bci2000_file

from .utils import OUTPUT_PATH

gui_file = bci2000_file


def test_scroll_data(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.grab().save(str(OUTPUT_PATH / 'open_01_start.png'))

    w.info.idx_filename.setStyleSheet("background-color: red;")
    w.grab().save(str(OUTPUT_PATH / 'open_02_open_dataset.png'))
    w.info.idx_filename.setStyleSheet("")

    w.info.open_dataset(str(gui_file))

    new_button = w.channels.layout().itemAt(0).itemAt(0).widget()
    new_button.setStyleSheet("background-color: red;")
    w.grab().save(str(OUTPUT_PATH / 'open_03_loaded.png'))
    new_button.setStyleSheet("")

    channel_make_group(w, png=True)

    # this shows selected channels and the apply button
    apply_button = w.channels.layout().itemAt(0).itemAt(3).widget()
    apply_button.setStyleSheet("background-color: red;")
    w.grab().save(str(OUTPUT_PATH / 'open_05_chan.png'))
    apply_button.setStyleSheet("")

    channel_apply(w, png=True)
    w.grab().save(str(OUTPUT_PATH / 'open_06_traces.png'))


def channel_make_group(w, png=False):
    w.channels.new_group(test_name='scalp')

    if png:
        w.grab().save(str(OUTPUT_PATH / 'open_04_channel_new.png'))

    chan_tab_i = w.channels.tabs.currentIndex()
    channelsgroup = w.channels.tabs.widget(chan_tab_i)
    channelsgroup.idx_l0.item(0).setSelected(True)
    channelsgroup.idx_l0.item(2).setSelected(True)
    channelsgroup.idx_l0.item(3).setSelected(True)


def channel_apply(w, png=False):

    apply_button = w.channels.layout().itemAt(0).itemAt(3).widget()
    assert apply_button.text().replace('&', '') == 'Apply'
    apply_button.click()

