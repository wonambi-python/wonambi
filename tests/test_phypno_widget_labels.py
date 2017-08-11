from phypno.scroll_data import MainWindow

from .test_phypno_scroll_data import gui_file

from .utils import OUTPUT_PATH


def test_widget_labels(qtbot):

    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))

    w.labels.table.setStyleSheet("background-color: red;")
    w.grab().save(str(OUTPUT_PATH / 'labels_01_table.png'))
    w.labels.table.setStyleSheet("")

    # change label of second channel
    w.labels.table.item(1, 1).setText('newlabel')
    w.labels.grab().save(str(OUTPUT_PATH / 'labels_02_newlabel.png'))

    w.labels.table.item(3, 1).setText('newlabel')
    w.labels.grab().save(str(OUTPUT_PATH / 'labels_03_duplicate.png'))

    assert not w.labels.idx_apply.isEnabled()

    # fix it
    w.labels.table.item(3, 1).setText('correctlabel')
    w.labels.grab().save(str(OUTPUT_PATH / 'labels_04_correct.png'))

    assert w.labels.idx_apply.isEnabled()
