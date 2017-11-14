from json import dump, load
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QToolBar,
                             QToolButton,
                             )

from wonambi.scroll_data import MainWindow

from .test_scroll_data import (channel_make_group,
                               find_in_qt,
                               )

from .paths import (gui_file,
                    channel_montage_file,
                    channel_montage_reref_file,
                    GUI_PATH,
                    )


def test_widget_channels(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    assert not w.channels.isEnabled()

    w.info.open_dataset(str(gui_file))

    assert w.channels.isEnabled()

    assert not w.channels.button_color.isEnabled()
    assert not w.channels.button_del.isEnabled()
    assert not w.channels.button_apply.isEnabled()
    channel_make_group(w)
    assert w.channels.button_color.isEnabled()
    assert w.channels.button_del.isEnabled()
    assert w.channels.button_apply.isEnabled()

    w.channels.button_apply.click()

    w.channels.grab().save(str(GUI_PATH / 'channels_01_onegroup.png'))

    w.channels.new_group(test_name='eog')
    chan_tab_i = w.channels.tabs.currentIndex()
    channelsgroup = w.channels.tabs.widget(chan_tab_i)

    channelsgroup.idx_l0.item(2).setSelected(True)
    w.channels.grab().save(str(GUI_PATH / 'channels_02_eog.png'))

    chan_tab_i = w.channels.tabs.currentIndex()
    channelsgroup = w.channels.tabs.widget(chan_tab_i)

    channelsgroup.idx_l0.item(2).setSelected(True)

    channelsgroup.idx_hp.setValue(20)
    channelsgroup.idx_hp.setStyleSheet("background-color: red;")
    w.channels.grab().save(str(GUI_PATH / 'channels_03_hp.png'))
    channelsgroup.idx_hp.setStyleSheet("")

    channelsgroup.idx_lp.setValue(0)
    channelsgroup.idx_lp.setStyleSheet("background-color: red;")
    w.channels.grab().save(str(GUI_PATH / 'channels_04_lp.png'))
    channelsgroup.idx_lp.setStyleSheet("")

    channelsgroup.idx_scale.setValue(10)
    channelsgroup.idx_scale.setStyleSheet("background-color: red;")
    w.channels.grab().save(str(GUI_PATH / 'channels_05_scale.png'))
    channelsgroup.idx_scale.setStyleSheet("")

    channelsgroup.idx_l1.setStyleSheet("background-color: red;")
    w.channels.grab().save(str(GUI_PATH / 'channels_06_ref.png'))
    channelsgroup.idx_l1.setStyleSheet("")

    channelsgroup.idx_reref.setStyleSheet("background-color: red;")
    w.channels.grab().save(str(GUI_PATH / 'channels_07_avgref.png'))
    channelsgroup.idx_reref.setStyleSheet("")

    button_apply = w.channels.button_apply
    button_apply.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'channels_08_apply.png'))
    button_apply.setStyleSheet("")

    button_apply.click()

    button_color = w.channels.button_color
    button_color.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'channels_09_color.png'))
    button_color.setStyleSheet("")

    w.channels.color_group(test_color=QColor('#ff4a87'))
    w.grab().save(str(GUI_PATH / 'channels_10_colored.png'))

    button_delete = w.channels.button_del
    button_delete.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'channels_11_delete.png'))
    button_delete.setStyleSheet("")
    button_delete.click()

    # delete also the first channel group
    assert w.channels.button_color.isEnabled()
    assert w.channels.button_del.isEnabled()
    assert w.channels.button_apply.isEnabled()
    button_delete.click()
    assert not w.channels.button_color.isEnabled()
    assert not w.channels.button_del.isEnabled()
    assert not w.channels.button_apply.isEnabled()


def test_widget_channels_save(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)

    assert not w.channels.action['save_channels'].isEnabled()
    w.info.open_dataset(str(gui_file))
    assert w.channels.action['save_channels'].isEnabled()

    channel_make_group(w)

    w.channels.new_group(test_name='eog')

    chan_tab_i = w.channels.tabs.currentIndex()
    channelsgroup = w.channels.tabs.widget(chan_tab_i)
    channelsgroup.idx_l0.item(2).setSelected(True)

    channelsgroup.idx_hp.setValue(20)
    channelsgroup.idx_lp.setValue(0)
    channelsgroup.idx_scale.setValue(10)
    w.channels.color_group(test_color=QColor('#ff4a87'))

    w.channels.button_apply.click()

    toolbar = w.findChild(QToolBar, 'File Management')
    button_save = find_in_qt(toolbar, QToolButton, "Save Montage")
    button_save.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'channels_12_save_chan.png'))
    button_save.setStyleSheet("")

    w.channels.save_channels(test_name=str(channel_montage_file))


def test_widget_channels_load(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    assert not w.channels.action['load_channels'].isEnabled()
    w.info.open_dataset(str(gui_file))
    assert w.channels.action['load_channels'].isEnabled()

    toolbar = w.findChild(QToolBar, 'File Management')
    button_load = find_in_qt(toolbar, QToolButton, "Load Montage")
    button_load.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'channels_13_load_chan.png'))
    button_load.setStyleSheet("")

    w.channels.load_channels(test_name=str(channel_montage_file))
    w.grab().save(str(GUI_PATH / 'channels_14_loaded.png'))


def test_widget_channels_reref(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))

    w.channels.new_group(test_name='reref')

    chan_tab_i = w.channels.tabs.currentIndex()
    channelsgroup = w.channels.tabs.widget(chan_tab_i)
    channelsgroup.idx_l0.item(0).setSelected(True)
    channelsgroup.idx_l0.item(1).setSelected(True)
    channelsgroup.idx_reref.click()
    w.channels.button_apply.click()

    w.channels.save_channels(test_name=str(channel_montage_reref_file))

    # add one channel that doesn't exist
    with channel_montage_file.open() as outfile:
        groups = load(outfile)
    groups[0]['chan_to_plot'].append('NOT EXIST')
    with channel_montage_file.open('w') as outfile:
        dump(groups, outfile, indent=' ')

    # load dataset, but ignore extra channel
    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    w.channels.load_channels(test_name=str(channel_montage_file))

    assert 'NOT EXIST' in w.statusBar().currentMessage()
