"""Widget to define channels, montage and filters.

"""
from logging import getLogger
lg = getLogger(__name__)

from copy import deepcopy

from PySide.QtGui import (QAbstractItemView,
                          QColor,
                          QColorDialog,
                          QComboBox,
                          QFormLayout,
                          QGridLayout,
                          QWidget,
                          QInputDialog,
                          QLabel,
                          QLineEdit,
                          QListWidget,
                          QListWidgetItem,
                          QPushButton,
                          QVBoxLayout,
                          )

EMPTY_GROUP = {'name': 'General',
               'chan_to_plot': [],
               'ref_chan': [],
               'color': QColor('black'),
               'filter': {'low_cut': None, 'high_cut': None},
               'scale': 1}
EMPTY_FILTER = ('None', '', 'none', '0')


class Channels(QWidget):
    """Allow user to choose channels, montage, and filters.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    chan_name : list of str
        list of all the channels
    groups : list of dict
        groups of channels, with keys: 'name', 'chan_to_plot', 'ref_chan',
        'color', 'filter'
    current : str
        name of the current group
    idx_grp : instance of QComboBox
        index of the channel names
    idx_l0 : instance of QListWidget
        index of the list of selected channels
    idx_l1 : instance of QListWidget
        index of the list of reference channels
    idx_hp : instance of QLineEdit
        text with information about high-pass filter
    idx_lp : instance of QLineEdit
        text with information about low-pass filter
    idx_scale : instance of QLineEdit
        text with information about the group-specific scaling

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.chan_name = None
        self.groups = [deepcopy(EMPTY_GROUP)]
        self.current = EMPTY_GROUP['name']

        self.idx_grp = None
        self.idx_l0 = None
        self.idx_l1 = None
        self.idx_hp = None
        self.idx_lp = None
        self.idx_scale = None

        self.create_channels()

    def create_channels(self):
        """Create the QWidget with the channel information."""
        lg.debug('Creating empty Info widget')

        addButton = QPushButton('New')
        addButton.clicked.connect(lambda: self.ask_name('new'))
        renameButton = QPushButton('Rename')
        renameButton.clicked.connect(lambda: self.ask_name('rename'))
        colorButton = QPushButton('Color')
        colorButton.clicked.connect(self.color_group)
        delButton = QPushButton('Delete')
        delButton.clicked.connect(self.delete_group)

        self.idx_grp = QComboBox()
        self.idx_grp.activated.connect(self.change_group_info)

        self.idx_l0 = QListWidget()
        self.idx_l1 = QListWidget()

        rerefButton = QPushButton('Average Ref')
        rerefButton.clicked.connect(self.average_reference)
        rerefButton.setToolTip('Use the average of all the channels being ' +
                               'plotted as reference.')

        self.idx_hp = QLineEdit('')
        self.idx_lp = QLineEdit('')
        self.idx_scale = QLineEdit('')

        applyButton = QPushButton('Apply')
        applyButton.clicked.connect(self.apply_changes)

        hdr = QGridLayout()
        hdr.addWidget(addButton, 0, 0)
        hdr.addWidget(renameButton, 0, 1)
        hdr.addWidget(colorButton, 1, 0)
        hdr.addWidget(delButton, 1, 1)

        filt = QFormLayout()
        filt.addRow('High-Pass', self.idx_hp)
        filt.addRow('Low-Pass', self.idx_lp)

        applyform = QFormLayout()
        applyform.addRow('Scaling', self.idx_scale)
        applyform.addRow(applyButton)

        reflayout = QVBoxLayout()
        reflayout.addWidget(self.idx_l1)
        reflayout.addWidget(rerefButton)

        layout = QGridLayout()
        layout.addWidget(self.idx_grp, 0, 0)
        layout.addLayout(hdr, 0, 1)
        layout.addWidget(QLabel('Channels to Visualize'), 1, 0)
        layout.addWidget(QLabel('Reference Channels'), 1, 1)
        layout.addWidget(self.idx_l0, 2, 0)
        layout.addLayout(reflayout, 2, 1)
        layout.addLayout(filt, 3, 0)
        layout.addLayout(applyform, 3, 1)

        self.setLayout(layout)

    def update_channels(self, chan_name):
        """Read the channels and updates the widget.

        Parameters
        ----------
        chan_name : list of str
            list of channels, to choose from.

        """
        lg.debug('Updating Channels widget')
        self.chan_name = chan_name
        self.display_channels()

    def display_channels(self):
        """Display the widget with the channels.

        Notes
        -----
        This function should be called when the dataset is read in memory, so
        it should clear the previous items in each widget.

        """
        lg.debug('Displaying Channels widget')

        self.idx_grp.clear()
        for one_grp in self.groups:
            lg.info('Adding channel group ' + one_grp['name'])
            self.idx_grp.addItem(one_grp['name'])
        self.current = one_grp['name']

        self.add_channels_to_list(self.idx_l0)
        self.add_channels_to_list(self.idx_l1)
        self.update_group_info()

    def add_channels_to_list(self, l):
        """Create list of channels (one for those to plot, one for ref).

        Parameters
        ----------
        l : instance of QListWidget
            one of the two lists (chan_to_plot or ref_chan)

        """
        l.clear()

        ExtendedSelection = QAbstractItemView.SelectionMode(3)
        l.setSelectionMode(ExtendedSelection)
        for chan in self.chan_name:
            item = QListWidgetItem(chan)
            l.addItem(item)

    def change_group_info(self):
        """When group changes, read old info and update GUI."""
        lg.info('Change group from ' + self.current + ' to '
                + self.idx_grp.currentText())
        self.read_group_info()
        self.update_group_info()

    def read_group_info(self):
        """Read the GUI and update the channel groups."""
        lg.info('Reading information about channel group from GUI')

        selectedItems = self.idx_l0.selectedItems()
        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())

        selectedItems = self.idx_l1.selectedItems()
        ref_chan = []
        for selected in selectedItems:
            ref_chan.append(selected.text())

        hp = self.idx_hp.text()
        if hp in EMPTY_FILTER:
            low_cut = None
        else:
            low_cut = float(hp)

        lp = self.idx_lp.text()
        if lp in EMPTY_FILTER:
            high_cut = None
        else:
            high_cut = float(lp)

        scale = self.idx_scale.text()

        idx = self.get_group_idx()
        one_group = self.groups[idx]
        one_group['chan_to_plot'] = chan_to_plot
        one_group['ref_chan'] = ref_chan
        one_group['filter']['low_cut'] = low_cut
        one_group['filter']['high_cut'] = high_cut
        one_group['scale'] = float(scale)

    def update_group_info(self):
        """Update the information in a group."""
        self.current = self.idx_grp.currentText()
        idx = self.get_group_idx()
        one_group = self.groups[idx]

        self.highlight_channels(self.idx_l0, one_group['chan_to_plot'])
        self.highlight_channels(self.idx_l1, one_group['ref_chan'])
        self.idx_hp.setText(str(one_group['filter']['low_cut']))
        self.idx_lp.setText(str(one_group['filter']['high_cut']))
        self.idx_scale.setText(str(one_group['scale']))

    def highlight_channels(self, l, selected_chan):
        """Highlight channels in the list of channels.

        Parameters
        ----------
        selected_chan : list of str
            channels to indicate as selected.

        """
        for row in range(l.count()):
            item = l.item(row)
            if item.text() in selected_chan:
                item.setSelected(True)
            else:
                item.setSelected(False)

    def average_reference(self):
        """Select in the reference all the channels in the main selection."""
        selectedItems = self.idx_l0.selectedItems()

        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())
        self.highlight_channels(self.idx_l1, chan_to_plot)

    def ask_name(self, action):
        """Prompt the user for a new name.

        Parameters
        ----------
        action : 'new' or 'rename'
            which action should be called after getting the new name.

        """
        self.inputdialog = QInputDialog()
        self.inputdialog.show()

        if action == 'new':
            self.inputdialog.textValueSelected.connect(self.new_group)
        if action == 'rename':
            self.inputdialog.textValueSelected.connect(self.rename_group)

    def new_group(self):
        """Create a new group of channels."""
        new_group = deepcopy(EMPTY_GROUP)
        new_group['name'] = self.inputdialog.textValue()
        lg.info('Adding new channel group ' + new_group['name'])

        self.groups.append(new_group)
        idx = self.idx_grp.currentIndex()
        self.idx_grp.insertItem(idx + 1, new_group['name'])
        self.idx_grp.setCurrentIndex(idx + 1)
        self.update_group_info()

    def rename_group(self):
        """Rename a group of channels."""
        new_grp_name = self.inputdialog.textValue()
        idx = self.get_group_idx()
        self.groups[idx]['name'] = new_grp_name
        self.current = new_grp_name
        lg.info('Renaming channel group ' + new_grp_name)

        idx = self.idx_grp.currentIndex()
        self.idx_grp.setItemText(idx, new_grp_name)

    def color_group(self):
        """Change color to a group of channels."""
        idx = self.get_group_idx()
        newcolor = QColorDialog.getColor(self.groups[idx]['color'])
        self.groups[idx]['color'] = newcolor

    def delete_group(self):
        """Delete one group of channels."""
        idx = self.idx_grp.currentIndex()
        self.idx_grp.removeItem(idx)
        self.groups.pop(idx)
        self.update_group_info()

    def apply_changes(self):
        """Apply changes to the plots."""
        self.read_group_info()
        self.parent.spectrum.update_spectrum()
        self.parent.overview.update_position()

    def get_group_idx(self):
        """Get index of self.group list (this is reused often)."""
        lg.debug('Current is {}'.format(self.current))
        return [x['name'] for x in self.groups].index(self.current)
