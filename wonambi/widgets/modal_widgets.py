from datetime import timedelta
from operator import itemgetter
from os.path import basename, splitext

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView,
                             QComboBox,
                             QDateTimeEdit,
                             QDialog,
                             QDialogButtonBox,
                             QFileDialog,
                             QFormLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit,
                             QListWidget,
                             QListWidgetItem,
                             QPushButton,
                             QSpinBox,
                             QVBoxLayout,
                             )

from .utils import FormMenu, FormFloat, FormBool, short_strings, STAGE_NAME


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
        Button box with Help, Ok and Cancel
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

        self.setWindowModality(Qt.ApplicationModal)
        self.groups = self.parent.channels.groups
        self.index = {}
        self.cycles = None

        self.create_widgets()

    def create_widgets(self):
        """Build basic components of dialog."""
        self.bbox = QDialogButtonBox(QDialogButtonBox.Help |
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_help = self.bbox.button(QDialogButtonBox.Help)
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


class EventAnalysisDialog(QDialog):
    """Dialog for specifying event analysis measures

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window
    group : dict
        information about groups from Channels
    index : dict of FormBool
        Contains information about parameters to analyze, for analyze_events.
    frequency : dict of FormFloat
        Contains lowcut and highcut frequencies for bandpassing.
    filename : str
        path/name of file to create
    cycles : list of tuple
        cycle start and end times, in seconds from recording start

    idx_evt_type : QComboBox
        Combo box of event types.
    idx_group : QComboBox
        Combo box of channel groups.
    idx_chan : QComboBox
        Combo box of all channels for selected group.
    """
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent

        self.setWindowTitle('Event analysis')
        self.setWindowModality(Qt.ApplicationModal)
        self.groups = self.parent.channels.groups
        self.idx_group = None
        self.idx_chan = None
        self.event_types = None
        self.idx_evt_type = None
        self.filename = None
        self.index = {}
        self.frequency = {}
        self.cycles = None

        self.create_dialog()

    def create_dialog(self):
        """Create the dialog."""
        bbox = QDialogButtonBox(QDialogButtonBox.Help | QDialogButtonBox.Ok |
                QDialogButtonBox.Cancel)
        self.idx_help = bbox.button(QDialogButtonBox.Help)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)
        bbox.clicked.connect(self.button_clicked)

        box0 = QGroupBox('Info')

        filebutton = QPushButton()
        filebutton.setText('Choose')
        filebutton.clicked.connect(self.save_as)
        self.idx_filename = filebutton

        event_box = QComboBox()
        if self.event_types is not None:
            for ev in self.event_types:
                event_box.addItem(ev)
        self.idx_evt_type = event_box

        chan_grp_box = QComboBox()
        for gr in self.groups:
            chan_grp_box.addItem(gr['name'])
        self.idx_group = chan_grp_box
        chan_grp_box.activated.connect(self.update_channels)

        chan_box = QComboBox()
        self.idx_chan = chan_box

        stage_box = QListWidget()
        stage_box.addItems(STAGE_NAME)
        stage_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_stage = stage_box

        flayout = QFormLayout()
        box0.setLayout(flayout)
        flayout.addRow('Filename',
                            self.idx_filename)
        flayout.addRow('Event type',
                            self.idx_evt_type)
        flayout.addRow('Channel group',
                            self.idx_group)
        flayout.addRow('Channel',
                            self.idx_chan)
        flayout.addRow('Stage(s)',
                            self.idx_stage)

        boxfilt = QGroupBox('Bandpass')

        self.frequency['locut'] = FormFloat()
        self.frequency['hicut'] = FormFloat()

        self.frequency['locut'].set_value(10)
        self.frequency['hicut'].set_value(16)

        flayout = QFormLayout()
        boxfilt.setLayout(flayout)
        flayout.addRow('Lowcut (Hz)',
                            self.frequency['locut'])
        flayout.addRow('Highcut (Hz)',
                            self.frequency['hicut'])

        box1 = QGroupBox('Parameters, global')

        self.index['count'] = FormBool('Count')
        self.index['density'] = FormBool('Density, per epoch of stage(s)')

        self.index['count'].setCheckState(Qt.Checked)
        self.index['density'].setCheckState(Qt.Checked)

        flayout = QFormLayout()
        box1.setLayout(flayout)
        flayout.addRow(self.index['count'])
        flayout.addRow(self.index['density'])

        box2 = QGroupBox('Parameters, per event')

        self.index['dur'] = FormBool('Duration (sec)')
        self.index['maxamp'] = FormBool(' Max. amplitude (uV)')
        self.index['ptp'] = FormBool('Peak-to-peak amplitude (uV)')
        self.index['peakf'] = FormBool('Peak frequency (Hz)')
        self.index['power'] = FormBool('Average power (uV^2)')
        self.index['rms'] = FormBool('RMS (uV)')

        self.index['dur'].setCheckState(Qt.Checked)
        self.index['maxamp'].setCheckState(Qt.Checked)
        self.index['ptp'].setCheckState(Qt.Checked)
        self.index['peakf'].setCheckState(Qt.Checked)
        self.index['power'].setCheckState(Qt.Checked)
        self.index['rms'].setCheckState(Qt.Checked)

        flayout = QFormLayout()
        box2.setLayout(flayout)
        flayout.addRow(self.index['dur'])
        flayout.addRow(self.index['maxamp'])
        flayout.addRow(self.index['ptp'])
        flayout.addRow(self.index['peakf'])
        flayout.addRow(self.index['power'])
        flayout.addRow(self.index['rms'])

        box3 = QGroupBox('Options')

        self.index['log'] = FormBool('Log transform all')
        self.freq_split = FormBool('Frequency split')
        self.cyc_split = FormBool('Cycle split')
        self.freq_cutoff = QLineEdit()

        self.index['log'].setCheckState(Qt.Unchecked)
        self.freq_split.setCheckState(Qt.Unchecked)
        self.freq_split.stateChanged.connect(self.update_fsplit)
        self.freq_cutoff.setEnabled(False)
        self.cyc_split.setCheckState(Qt.Unchecked)

        fslayout = QHBoxLayout()
        fslayout.addWidget(self.freq_split)
        fslayout.addWidget(self.freq_cutoff)

        flayout = QFormLayout()
        box3.setLayout(flayout)
        flayout.addRow(self.index['log'])
        flayout.addRow(fslayout)
        flayout.addRow(self.cyc_split)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(box0)
        vlayout.addWidget(boxfilt)
        vlayout.addWidget(box1)
        vlayout.addWidget(box2)
        vlayout.addWidget(box3)
        vlayout.addStretch(1)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button is self.idx_ok:

            if self.filename is None:
                return

            freqs = (self.frequency['locut'].get_value(),
                     self.frequency['hicut'].get_value())

            if None in freqs:
                self.parent.statusBar().showMessage(
                        'Specify bandpass frequencies')
                return

            filename = self.filename
            evt_type = self.idx_evt_type.currentText()
            chan = self.idx_chan.currentText()
            chan_name = chan + ' (' + self.idx_group.currentText() + ')'
            params = [k for k, v in self.index.items() if v.get_value()]
            stage = self.idx_stage.selectedItems()
            cycles = None
            fsplit = None

            if stage == []:
                stage = None
            else:
                stage = [x.text() for x in self.idx_stage.selectedItems()]

            if self.cyc_split.get_value():
                cycles = self.cycles

            if self.freq_split.get_value():
                fsplit = float(self.freq_cutoff.text())

            self.parent.notes.read_data(chan, self.one_grp)

            summary, events = self.parent.notes.analyze_events(evt_type,
                                                             chan_name,
                                                             stage,
                                                             params,
                                                             frequency=freqs,
                                                             cycles=cycles,
                                                             fsplit=fsplit)

            self.parent.notes.annot.export_event_data(filename, summary,
                                                      events, cycles=cycles,
                                                      fsplit=fsplit)

            self.accept()

        if button is self.idx_cancel:
            self.reject()

        if button is self.idx_help:
            self.parent.show_evt_analysis_help()

    def save_as(self):
        """Dialog for getting name, location of annotation export csv."""
        filename = splitext(
                self.parent.notes.annot.xml_file)[0] + '_event_data.csv'
        filename, _ = QFileDialog.getSaveFileName(self, 'Export event data',
                                                  filename,
                                                  'Sleep stages (*.csv)')
        if filename == '':
            return

        self.filename = filename
        short_filename = short_strings(basename(self.filename))
        self.idx_filename.setText(short_filename)

    def update_types(self):
        """Update the event types list when dialog is opened."""
        self.event_types = self.parent.notes.annot.event_types
        self.idx_evt_type.clear()
        for ev in self.event_types:
            self.idx_evt_type.addItem(ev)

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

        for chan in self.one_grp['chan_to_plot']:
            self.idx_chan.addItem(chan)

    def update_cycles(self):
        """Enable cycles checkbox only if there are cycles marked, with no
        errors."""
        try:
            self.cycles = self.parent.notes.annot.get_cycles()

        except ValueError as msg:
            self.cyc_split.setEnabled(False)
            self.parent.statusBar().showMessage('There is a problem with the '
                                 'cycle markers: ' + str(msg))

        else:
            if self.cycles is None:
                self.cyc_split.setEnabled(False)
            else:
                self.cyc_split.setEnabled(True)

    def update_fsplit(self):
        """Enable/disable power lowcut and highcut rows."""
        if self.freq_split.get_value() == True:
            self.freq_cutoff.setEnabled(True)
            self.index['peakf'].set_value(True)
            self.index['peakf'].setEnabled(False)
        else:
            self.freq_cutoff.setEnabled(False)
            self.index['peakf'].setEnabled(True)


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
