
from phypno.scroll_data import MainWindow

from .test_phypno_ioeeg_ktlx import ktlx_file

def test_scroll_data(qtbot):

    w = MainWindow()
    w.show()
    qtbot.addWidget(w)

    w.info.open_dataset(str(ktlx_file))
