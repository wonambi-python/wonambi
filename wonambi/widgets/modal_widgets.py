from datetime import timedelta

from PyQt5.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QDateTimeEdit,
                             QSpinBox,
                             QLabel,
                             QFormLayout,
                             )


class DateTimeDialog(QDialog):

    def __init__(self, title, start_time, dur):
        self.start_time = start_time
        self.dur = dur
        super().__init__()
        self.setWindowTitle(title)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)

        bbox.clicked.connect(self.button_clicked)

        self.seconds = QSpinBox()
        self.seconds.setMinimum(0)
        self.seconds.setMaximum(dur)

        self.seconds.valueChanged.connect(self.changed_spin)

        q = QDateTimeEdit(start_time)
        q.setMinimumDate(start_time)
        et = start_time + timedelta(seconds=dur)
        q.setMaximumDate(et)
        q.setDisplayFormat('dd-MMM-yyyy HH:mm:ss')
        q.dateTimeChanged.connect(self.changed_datetime)
        self.idx_datetime = q

        f = QFormLayout()
        f.addRow('', QLabel('Enter ' + title + ' time'))
        f.addRow('Seconds from recording start', self.seconds)
        f.addRow('Absolute time', self.idx_datetime)
        f.addRow(bbox)

        self.setLayout(f)
        self.setModal(True)
        self.show()

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

        self.seconds.blockSignals(True)
        self.seconds.setValue(val)
        self.seconds.blockSignals(False)
