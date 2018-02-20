"""Widget with general information about the dataset."""
from datetime import timedelta
from functools import partial
from logging import getLogger
from os.path import basename, dirname, splitext

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QAbstractItemView,
                             QAction,
                             QDialog,
                             QDialogButtonBox,
                             QFileDialog,
                             QFormLayout,
                             QGroupBox,
                             QLabel,
                             QListWidget,
                             QPushButton,
                             QHBoxLayout,
                             QVBoxLayout,
                             QWidget,
                             )

from .. import Dataset
from ..ioeeg import write_wonambi, write_edf
from .utils import (short_strings, ICON, keep_recent_datasets,
                    choose_file_or_dir, FormBool, FormFloat, FormMenu)

lg = getLogger(__name__)
settings = QSettings("wonambi", "wonambi")


class Info(QWidget):
    """Display information about the dataset.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    filename : str
        the full path of the file.
    dataset : instance of wonambi.Dataset
        the dataset already read in.
    markers : list
        list of the markers in the dataset

    idx_filename : QPushButton
        button to select dataset / show current dataset
    idx_s_freq : QLabel
        show sampling frequency
    idx_n_chan : QLabel
        show number of channels
    idx_start_time : QLabel
        show start time of the dataset
    idx_end_time : QLabel
        show end time of the dataset

    idx_start : QLabel
        show start time of the window
    idx_length : QLabel
        show length of the time window
    idx_scaling : QLabel
        show current scaling
    idx_distance : QLabel
        show current distance between traces
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.filename = None
        self.dataset = None
        self.markers = []

        # about the recordings
        self.idx_filename = None
        self.idx_s_freq = None
        self.idx_n_chan = None
        self.idx_start_time = None
        self.idx_end_time = None
        # about the visualization
        self.idx_start = None
        self.idx_length = None
        self.idx_scaling = None
        self.idx_distance = None

        self.create()
        self.create_action()

    def create(self):
        """Create the widget layout with all the information."""
        b0 = QGroupBox('Dataset')
        form = QFormLayout()
        b0.setLayout(form)

        open_rec = QPushButton('Open Dataset...')
        open_rec.clicked.connect(self.open_dataset)
        open_rec.setToolTip('Click here to open a new recording')
        self.idx_filename = open_rec
        self.idx_s_freq = QLabel('')
        self.idx_n_chan = QLabel('')
        self.idx_start_time = QLabel('')
        self.idx_end_time = QLabel('')

        form.addRow('Filename:', self.idx_filename)
        form.addRow('Sampl. Freq:', self.idx_s_freq)
        form.addRow('N. Channels:', self.idx_n_chan)
        form.addRow('Start Time: ', self.idx_start_time)
        form.addRow('End Time: ', self.idx_end_time)

        b1 = QGroupBox('View')
        form = QFormLayout()
        b1.setLayout(form)

        self.idx_start = QLabel('')
        self.idx_start.setToolTip('Start time in seconds from the beginning of'
                                  ' the recordings')
        self.idx_length = QLabel('')
        self.idx_length.setToolTip('Duration of the time window in seconds')
        self.idx_scaling = QLabel('')
        self.idx_scaling.setToolTip('Global scaling for all the channels')
        self.idx_distance = QLabel('')
        self.idx_distance.setToolTip('Visual distances between the traces of '
                                     'individual channels')

        form.addRow('Start Time:', self.idx_start)
        form.addRow('Length:', self.idx_length)
        form.addRow('Scaling:', self.idx_scaling)
        form.addRow('Distance:', self.idx_distance)

        layout = QVBoxLayout()
        layout.addWidget(b0)
        layout.addWidget(b1)

        self.setLayout(layout)

    def create_action(self):
        """Create actions associated with this widget.

        Notes
        -----
        I think that this should be a function or a property.

        The good thing about the property is that it is updated every time you
        run it (for example, if you change some parameters in the settings).
        The main drawback is that you cannot reference back to the QAction, as
        it creates new ones every time.
        """
        output = {}

        act = QAction(QIcon(ICON['open_rec']), 'Open Dataset...', self)
        act.setShortcut(QKeySequence.Open)
        act.triggered.connect(self.open_dataset)
        output['open_dataset'] = act

        max_dataset_history = self.parent.value('max_dataset_history')
        recent_recs = keep_recent_datasets(max_dataset_history)

        act = []
        for one_recent_rec in recent_recs:
            act_recent = QAction(one_recent_rec, self)
            act_recent.triggered.connect(partial(self.open_dataset,
                                                 one_recent_rec))
            act.append(act_recent)
        output['open_recent'] = act

        act = QAction('Export dataset...', self)
        act.triggered.connect(self.parent.show_export_dataset_dialog)
        act.setEnabled(False)
        output['export'] = act
        
        self.action = output

    def open_dataset(self, recent=None, debug_filename=None):
        """Open a new dataset.

        Parameters
        ----------
        recent : path to file
            one of the recent datasets to read
        """
        if recent:
            filename = recent

        elif debug_filename is not None:
            filename = debug_filename

        else:
            try:
                dir_name = dirname(self.filename)
            except (AttributeError, TypeError):
                dir_name = self.parent.value('recording_dir')

            file_or_dir = choose_file_or_dir()
            if file_or_dir == 'dir':
                filename = QFileDialog.getExistingDirectory(self,
                                                            'Open directory',
                                                            dir_name)
            elif file_or_dir == 'file':
                filename, _ = QFileDialog.getOpenFileName(self, 'Open file',
                                                          dir_name)

            elif file_or_dir == 'abort':
                return

        if filename == '':
            return

        # clear previous dataset once the user opens another dataset
        if self.dataset is not None:
            self.parent.reset()

        self.parent.statusBar().showMessage('Reading dataset: ' +
                                            basename(filename))
        lg.info('Reading dataset: ' + str(filename))
        self.filename = filename # temp
        self.dataset = Dataset(filename) #temp
#==============================================================================
#         try:
#             self.filename = filename
#             self.dataset = Dataset(filename)
#         except FileNotFoundError:
#             msg = 'File ' + basename(filename) + ' cannot be read'
#             self.parent.statusBar().showMessage(msg)
#             lg.info(msg)
#             error_dialog = QErrorMessage()
#             error_dialog.setWindowTitle('Error opening dataset')
#             error_dialog.showMessage(msg)
#             if debug_filename is None:
#                 error_dialog.exec()
#             return
# 
#         except BaseException as err:
#             self.parent.statusBar().showMessage(str(err))
#             lg.info('Error ' + str(err))
#             error_dialog = QErrorMessage()
#             error_dialog.setWindowTitle('Error opening dataset')
#             error_dialog.showMessage(str(err))
#             if debug_filename is None:
#                 error_dialog.exec()
#             return
#==============================================================================

        self.action['export'].setEnabled(True)

        self.parent.statusBar().showMessage('')

        self.parent.update()

    def display_dataset(self):
        """Update the widget with information about the dataset."""
        header = self.dataset.header

        self.parent.setWindowTitle(basename(self.filename))
        short_filename = short_strings(basename(self.filename))
        self.idx_filename.setText(short_filename)
        self.idx_s_freq.setText(str(header['s_freq']))
        self.idx_n_chan.setText(str(len(header['chan_name'])))
        start_time = header['start_time'].strftime('%b-%d %H:%M:%S')
        self.idx_start_time.setText(start_time)
        end_time = (header['start_time'] +
                    timedelta(seconds=header['n_samples'] / header['s_freq']))
        self.idx_end_time.setText(end_time.strftime('%b-%d %H:%M:%S'))

    def display_view(self):
        """Update information about the size of the traces."""
        self.idx_start.setText(str(self.parent.value('window_start')))
        self.idx_length.setText(str(self.parent.value('window_length')))
        self.idx_scaling.setText(str(self.parent.value('y_scale')))
        self.idx_distance.setText(str(self.parent.value('y_distance')))

    def reset(self):
        """Reset widget to original state."""
        self.filename = None
        self.dataset = None

        # about the recordings
        self.idx_filename.setText('Open Recordings...')
        self.idx_s_freq.setText('')
        self.idx_n_chan.setText('')
        self.idx_start_time.setText('')
        self.idx_end_time.setText('')

        # about the visualization
        self.idx_scaling.setText('')
        self.idx_distance.setText('')
        self.idx_length.setText('')
        self.idx_start.setText('')
        
    def export(self, new_format, filename=None, chan=None, begtime=None, 
               endtime=None):
        """Export current dataset to wonambi format (.won).
        
        Parameters
        ----------
        new_format : str
            Format for exported record: 'edf' or 'wonambi'
        filename : str or PosixPath
            filename to export to
        chan : list of str, opt
            list of original channel names to export. if None, all channels are
            exported
        begtime : int or datedelta or datetime
            start of the data to read;
            if it's int or float, it's assumed it's s;
            if it's timedelta, it's assumed from the start of the recording;
            if it's datetime, it's assumed it's absolute time.
        endtime : int or datedelta or datetime
            end of the data to read;
            if it's int or float, it's assumed it's s;
            if it's timedelta, it's assumed from the start of the recording;
            if it's datetime, it's assumed it's absolute time.
        """
        dataset = self.dataset
        subj_id = dataset.header['subj_id']
        if filename is None:
            filename = dataset.filename
        
        data = dataset.read_data(chan=chan, begtime=begtime, endtime=endtime)
        
        if 'wonambi' == new_format:
            write_wonambi(data, filename, subj_id=subj_id)
            
        elif 'edf' == new_format:
            write_edf(data, filename, subj_id=subj_id)
            
        else:
            self.parent.statusBar().showMessage('Format unrecognized.')

        
class ExportDatasetDialog(QDialog):
    """Dialog for choosing export dataset options."""
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent
        self.setWindowModality(Qt.ApplicationModal)

        self.create_dialog()
    
    def create_dialog(self):
        """Create the dialog."""
        self.bbox = QDialogButtonBox(QDialogButtonBox.Help |
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.idx_cancel = self.bbox.button(QDialogButtonBox.Cancel)
        
        filebutton = QPushButton()
        filebutton.setText('Choose')
        self.idx_filename = filebutton
        
        self.new_format = FormMenu(['EDF', 'Wonambi'])
        self.all_time = FormBool('Entire length of record')
        self.all_chan = FormBool('All channels')
        
        self.times = {}
        self.times['beg'] = FormFloat()
        self.times['end'] = FormFloat()
        
        chan_box = QListWidget()
        chan_box.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.idx_chan = chan_box
        
        filebutton.clicked.connect(self.save_as)
        self.all_time.connect(self.toggle_buttons)
        self.all_chan.connect(self.toggle_buttons)
        self.bbox.clicked.connect(self.button_clicked)

        self.all_time.set_value(True)
        self.all_chan.set_value(True)
        
        form = QFormLayout()
        form.addRow('Filename',
                    filebutton)
        #form.addRow('Format', self.new_format)
        form.addRow(self.all_time)
        form.addRow('Start time (sec)', 
                    self.times['beg'])
        form.addRow('End time (sec)',
                    self.times['end'])
        form.addRow(self.all_chan)
        form.addRow('Channel(s)',
                    self.idx_chan)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(form)
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
            
            #new_format = self.new_format.get_value().lower()
            new_format = 'edf'
            chan = None
            beg = None
            end = None
            
            if not self.all_time.get_value():
                beg = self.times['beg'].get_value()
                end = self.times['end'].get_value()
                
            if not self.all_chan.get_value():
                chan = self.get_channels()
                
            self.parent.info.export(new_format, filename=self.filename, 
                                    chan=chan, begtime=beg, endtime=end)
            
            self.accept()                
        
        if button is self.idx_cancel:
            self.reject()
    
    def toggle_buttons(self):
        """Turn buttons on and off."""
        all_time_on = self.all_time.get_value()
        all_chan_on = self.all_chan.get_value()
        
        self.times['beg'].setEnabled(not all_time_on)
        self.times['end'].setEnabled(not all_time_on)
        self.idx_chan.setEnabled(not all_chan_on)
        
    def save_as(self):
        """Dialog for getting name, location of dataset export."""
        filename = splitext(self.filename)[0] + '.edf'
        filename, _ = QFileDialog.getSaveFileName(self, 'Export dataset',
                                                  filename,
                                                  'European Data Format '
                                                  '(*.edf)')
        if filename == '':
            return

        self.filename = filename
        short_filename = short_strings(basename(self.filename))
        self.idx_filename.setText(short_filename)
        
    def get_channels(self):
        """Get the selected channel(s in order). """
        selectedItems = self.idx_chan.selectedItems()
        selected_chan = [x.text() for x in selectedItems]
        chan_in_order = []
        for chan in self.chan:
            if chan in selected_chan:
                chan_in_order.append(chan)

        return chan_in_order
    
    def update(self):
        """Get info from dataset before opening dialog."""
        self.filename = self.parent.info.dataset.filename
        
        self.chan = self.parent.info.dataset.header['chan_name']
        for chan in self.chan:
            self.idx_chan.addItem(chan)
        
    

        
