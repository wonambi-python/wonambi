from wonambi.scroll_data import MainWindow

from .test_scroll_data import (channel_make_group,
                               find_pushbutton,
                               )

from .paths import (gui_file,
                    GUI_PATH,
                    )


def test_widget_channels(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    assert not w.channels.isEnabled()

    w.info.open_dataset(str(gui_file))

    assert w.channels.isEnabled()

    channel_make_group(w)
    find_pushbutton(w.channels, 'Apply').click()

    w.channels.grab().save(str(GUI_PATH / 'channels_01_onegroup.png'))

    w.channels.new_group(test_name='eog')
    w.channels.grab().save(str(GUI_PATH / 'channels_02_eog.png'))
