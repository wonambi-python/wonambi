from wonambi.scroll_data import MainWindow

from .test_scroll_data import (channel_make_group,
                               channel_apply,
                               )

from .paths import (gui_file,
                    )


def test_widget_channels(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    assert not w.channels.isEnabled()

    w.info.open_dataset(str(gui_file))

    assert w.channels.isEnabled()
