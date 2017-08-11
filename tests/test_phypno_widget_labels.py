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
