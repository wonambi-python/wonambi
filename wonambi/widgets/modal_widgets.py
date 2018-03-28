from datetime import timedelta
from operator import itemgetter

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView,
                             QComboBox,
                             QDateTimeEdit,
                             QDialog,
                             QDialogButtonBox,
                             QFileDialog,
                             QFormLayout,
                             QLabel,
                             QListWidget,
                             QListWidgetItem,
                             QPushButton,
                             QSpinBox,
                             )

from .utils import FormMenu, STAGE_NAME


class ChannelDialog(QDialog):
    """Template dialog for event detection.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window
    groups : list of dict
        information about groups from Channels
    index : dict of FormFloat
        Contains detection parameters.

    bbox : QDialogButtonBox
        Button box with Ok and Cancel
    idx_group : FormMenu
        Combo box of channel groups.
    idx_chan : QListWidget
        List widget containing all channels for selected group.
    idx_stage :  QListWidget
        List widget containing all stages.
    idx_cycle : QListWidget
        List widget containing all marked cycles.
    one_grp : dict
        info about selected group from Channels
    """
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent

        self.setWindowModality(Qt.WindowModal)
        self.groups = self.parent.channels.groups
        self.index = {}
        self.cycles = None

        self.create_widgets()

    def create_widgets(self):
        """Build basic components of dialog."""
        self.bbox = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = self.bbox.button(QDialogButtonBox.Cancel)

        self.idx_group = FormMenu([gr['name'] for gr in self.groups])

        chan_box = QListWidget()
        self.idx_chan = chan_box

        stage_box = QListWidget()
        stage_box.addItems(STAGE_NAME)
        stage_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_stage = stage_box

        cycle_box = QListWidget()
        cycle_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_cycle = cycle_box

    def update_groups(self):
        """Update the channel groups list when dialog is opened."""
        self.groups = self.parent.channels.groups
        self.idx_group.clear()
        for gr in self.groups:
            self.idx_group.addItem(gr['name'])

        self.update_channels()

    def update_channels(self):
        """Update the channels list when a new group is selected."""
        group_dict = {k['name']: i for i, k in enumerate(self.groups)}
        group_index = group_dict[self.idx_group.currentText()]
        self.one_grp = self.groups[group_index]

        self.idx_chan.clear()

        self.idx_chan.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for chan in self.one_grp['chan_to_plot']:
            name = chan + '—(' + '+'.join(self.one_grp['ref_chan']) + ')'
            item = QListWidgetItem(name)
            self.idx_chan.addItem(item)

    def update_cycles(self):
        """Enable cycles checkbox only if there are cycles marked, with no
        errors."""
        self.idx_cycle.clear()

        try:
            self.cycles = self.parent.notes.annot.get_cycles()

        except ValueError as err:
            self.idx_cycle.setEnabled(False)
            msg = 'There is a problem with the cycle markers: ' + str(err)
            self.parent.statusBar().showMessage(msg)

        else:
            if self.cycles is None:
                self.idx_cycle.setEnabled(False)
            else:
                self.idx_cycle.setEnabled(True)
                for i in range(len(self.cycles)):
                    self.idx_cycle.addItem(str(i+1))

    def get_channels(self):
        """Get the selected channel(s in order).

        Returns
        -------
        list of str
            name of each channel (without group), in original record order
        """
        selectedItems = self.idx_chan.selectedItems()
        selected_chan = [x.text().split('—')[0] for x in selectedItems]
        chan_in_order = []
        for chan in self.one_grp['chan_to_plot']:
            if chan in selected_chan:
                chan_in_order.append(chan)

        return chan_in_order

    def get_cycles(self):
        """Get the selected cycle(s in order).

        Returns
        -------
        list of tuple
            Each tuple is (start time (sec), end time (sec), index (starting
            at 1)."""
        idx_cyc_sel = [
                int(x.text()) - 1 for x in self.idx_cycle.selectedItems()]
        if not idx_cyc_sel:
            cycle = None
        else:
            cycle = itemgetter(*idx_cyc_sel)(self.cycles)
            if len(idx_cyc_sel) == 1:
                cycle = [cycle]

        return cycle


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
        self.idx_datetime.setMinimumDate(start_time)
        self.idx_datetime.setMaximumDate(end_time)
        self.idx_datetime.setDisplayFormat('dd-MMM-yyyy HH:mm:ss')
        self.idx_datetime.dateTimeChanged.connect(self.changed_datetime)

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


class SVGDialog(QDialog):

    def __init__(self, dirname):
        super().__init__()

        self.dirname = str(dirname)

        self.setWindowTitle('Export to SVG')

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)
        bbox.clicked.connect(self.button_clicked)

        self.idx_list = QComboBox()
        self.idx_list.addItems(['Traces', 'Overview'])

        self.idx_file = QPushButton()
        self.idx_file.setText('(click to choose file)')
        self.idx_file.clicked.connect(self.select_filename)

        layout = QFormLayout()
        layout.addRow('Which Panel', self.idx_list)
        layout.addRow('File Name', self.idx_file)
        layout.addRow(bbox)

        self.setLayout(layout)

    def button_clicked(self, button):
        if button == self.idx_ok:
            self.accept()

        elif button == self.idx_cancel:
            self.reject()

    def select_filename(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export screenshot', self.dirname, 'Image (*.svg)')

        if filename == '':
            return

        self.idx_file.setText(filename)
