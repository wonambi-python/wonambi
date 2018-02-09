from datetime import timedelta

from PyQt5.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QDateTimeEdit,
                             QSpinBox,
                             QLabel,
                             QFormLayout,
                             )


class DateTimeDialog(QDialog):
    """Dialog to specify time in the recordings, either as seconds from the
    start of the recordings or absolute time.

    Parameters
    ----------
    title : str
        'Lights out' or 'Lights on'
    start_time : datetime
        absolute start time of the recordings
    dur : int
        total duration of the recordings

    Notes
    -----
    The value of interest is in self.idx_seconds.value(), which is seconds
    from the start of the recordings.
    """
    def __init__(self, title, start_time, dur):
        super().__init__()

        self.start_time = start_time
        self.dur = dur
        end_time = start_time + timedelta(seconds=dur)

        self.setWindowTitle(title)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)

        bbox.clicked.connect(self.button_clicked)

        self.idx_seconds = QSpinBox()
        self.idx_seconds.setMinimum(0)
        self.idx_seconds.setMaximum(dur)
        self.idx_seconds.valueChanged.connect(self.changed_spin)

        self.idx_datetime = QDateTimeEdit(start_time)
        self.idx_datetimesetMinimumDate(start_time)
        self.idx_datetimesetMaximumDate(end_time)
        self.idx_datetimesetDisplayFormat('dd-MMM-yyyy HH:mm:ss')
        self.idx_datetimedateTimeChanged.connect(self.changed_datetime)

        layout = QFormLayout()
        layout.addRow('', QLabel('Enter ' + title + ' time'))
        layout.addRow('Seconds from recording start', self.idx_seconds)
        layout.addRow('Absolute time', self.idx_datetime)
        layout.addRow(bbox)

        self.setLayout(layout)

    def button_clicked(self, button):
        if button == self.idx_ok:
            self.accept()

        elif button == self.idx_cancel:
            self.reject()

    def changed_spin(self, i):
        self.idx_datetime.blockSignals(True)
        self.idx_datetime.setDateTime(self.start_time + timedelta(seconds=i))
        self.idx_datetime.blockSignals(False)

    def changed_datetime(self, dt):
        val = (dt.toPyDateTime() - self.start_time).total_seconds()

        if val < 0 or val >= self.dur:
            val = min(self.dur, max(val, 0))
            self.changed_spin(val)

        self.idx_seconds.blockSignals(True)
        self.idx_seconds.setValue(val)
        self.idx_seconds.blockSignals(False)
