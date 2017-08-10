
from phypno.scroll_data import MainWindow

from .test_phypno_ioeeg_blackrock import ns4_file

from .utils import OUTPUT_PATH


def test_scroll_data(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.grab().save(str(OUTPUT_PATH / '01_start.png'))

    w.info.open_dataset(str(ns4_file))
    w.grab().save(str(OUTPUT_PATH / '02_loaded.png'))

    w.channels.new_group(test_name='test_group_0')

    chan_tab_i = w.channels.tabs.currentIndex()
    channelsgroup = w.channels.tabs.widget(chan_tab_i)
    channelsgroup.idx_l0.item(0).setSelected(True)

    apply_button = w.channels.layout().itemAt(0).itemAt(3).widget()
    assert apply_button.text().replace('&', '') == 'Apply'
    apply_button.click()
