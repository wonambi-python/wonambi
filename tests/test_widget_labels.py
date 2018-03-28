from PyQt5.QtWidgets import QPushButton

from wonambi.scroll_data import MainWindow

from .test_scroll_data import (channel_make_group,
                               find_in_qt,
                               )

from .paths import (GUI_PATH,
                    gui_file,
                    SAMPLE_PATH,
                    )


def test_widget_labels(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    assert not w.labels.isEnabled()

    w.info.open_dataset(str(gui_file))
    labels_orig = w.labels.chan_name

    assert w.labels.isEnabled()

    w.action['dockwidgets'][1].trigger()
    w.labels.table.setStyleSheet("background-color: red;")
    w.grab().save(str(GUI_PATH / 'labels_01_table.png'))
    w.labels.table.setStyleSheet("")

    # change label of second channel
    w.labels.table.item(1, 1).setText('newlabel')
    w.labels.grab().save(str(GUI_PATH / 'labels_02_newlabel.png'))

    w.labels.table.item(3, 1).setText('newlabel')
    w.labels.grab().save(str(GUI_PATH / 'labels_03_duplicate.png'))

    assert not w.labels.idx_apply.isEnabled()

    # fix it
    w.labels.table.item(3, 1).setText('correctlabel')
    w.labels.grab().save(str(GUI_PATH / 'labels_04_correct.png'))

    assert w.labels.idx_apply.isEnabled()

    # cancel should reset the list
    labels_changed = w.labels._read_labels()
    w.labels.idx_cancel.click()
    labels_cancel = w.labels._read_labels()
    assert labels_cancel == labels_orig
    assert labels_cancel != labels_changed

    # apply
    w.labels.table.item(2, 1).setText('newlabel')
    w.labels.idx_apply.click()

    assert w.channels.isEnabled()

    channel_make_group(w)
    find_in_qt(w.channels, QPushButton, 'Apply').click()
    w.grab().save(str(GUI_PATH / 'labels_05_traces.png'))

    # load data
    w.labels.idx_load.setStyleSheet("background-color: red;")
    w.labels.grab().save(str(GUI_PATH / 'labels_06_load_button.png'))
    w.labels.idx_load.setStyleSheet("")

    labels_file = SAMPLE_PATH / 'labels_file.csv'
    with labels_file.open('w') as f:
        f.write('newchan1, newchan2\tnewchan3;\nnewchan5')

    w.labels.load_labels(test_name=str(labels_file))
    w.labels.grab().save(str(GUI_PATH / 'labels_07_loaded.png'))
