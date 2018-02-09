from datetime import datetime
from PyQt5.QtCore import QDateTime

from wonambi.widgets.modal_widgets import DateTimeDialog
from .paths import GUI_PATH


start_time = datetime(2018, 1, 1, 12, 0, 0)
duration = 120


def test_widget_labels(qtbot):
    d = DateTimeDialog('lights out', start_time, duration)
    qtbot.addWidget(d)

    d.idx_seconds.setValue(-10)
    assert d.idx_seconds.value() == 0

    d.idx_seconds.setValue(duration + 10)
    assert d.idx_seconds.value() == duration

    new_datetime = QDateTime(2018, 1, 1, 11, 30, 0)
    d.changed_datetime(new_datetime)
    assert d.idx_seconds.value() == 0

    # how to test this explicitly?
    d.button_clicked(d.idx_ok)
    d.button_clicked(d.idx_cancel)

    d.grab().save(str(GUI_PATH / 'analysis_02_timedialog.png'))
