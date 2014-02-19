from logging import getLogger
lg = getLogger(__name__)

from PySide.QtGui import (QAbstractItemView,
                          QColor,
                          QColorDialog,
                          QComboBox,
                          QFormLayout,
                          QGridLayout,
                          QGroupBox,
                          QInputDialog,
                          QLabel,
                          QLineEdit,
                          QListWidget,
                          QListWidgetItem,
                          QPushButton,
                          QVBoxLayout,
                          )


class Channels(QGroupBox):
    """Allow user to choose channels, and filters.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    chan_name : list of str
        list of all the channels
    groups : list of dict
        groups of channels, with keys: 'name', 'chan_to_plot', 'ref_chan',
        'color', 'filter'

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.chan_name = None
        self.groups = [{'name': 'general',
                      'chan_to_plot': [],
                      'ref_chan': [],
                      'color': QColor('black'),
                      'filter': {'low_cut': None, 'high_cut': None},
                      'scale': 1}, ]

    def update_channels(self, chan_name):
        """Read the channels and updates the widget.

        Parameters
        ----------
        chan_name : list of str
            list of channels, to choose from.

        """
        self.chan_name = chan_name
        self.display_channels()

    def display_channels(self):
        """Display the widget with the channels.

        """
        addButton = QPushButton('New')
        addButton.clicked.connect(lambda: self.ask_name('new'))
        renameButton = QPushButton('Rename')
        renameButton.clicked.connect(lambda: self.ask_name('rename'))
        colorButton = QPushButton('Color')
        colorButton.clicked.connect(self.color_group)
        self.colorButton = colorButton
        delButton = QPushButton('Delete')
        delButton.clicked.connect(self.delete_group)

        self.list_grp = QComboBox()
        for one_grp in self.groups:
            self.list_grp.addItem(one_grp['name'])

        self.list_grp.activated.connect(self.update_chan_grp)
        self.current = self.list_grp.currentText()

        self.l0 = QListWidget()
        self.create_list(self.l0)
        self.l1 = QListWidget()
        self.create_list(self.l1)

        rerefButton = QPushButton('Average Ref')
        rerefButton.clicked.connect(self.average_reference)
        rerefButton.setToolTip('Use the average of all the channels being ' +
                               'plotted as reference.')

        self.hpEdit = QLineEdit('None')
        self.lpEdit = QLineEdit('None')

        self.scaleEdit = QLineEdit(str(1))

        applyButton = QPushButton('Apply')
        applyButton.clicked.connect(self.apply_changes)

        hdr = QGridLayout()
        hdr.addWidget(addButton, 0, 0)
        hdr.addWidget(renameButton, 0, 1)
        hdr.addWidget(colorButton, 1, 0)
        hdr.addWidget(delButton, 1, 1)

        filt = QFormLayout()
        filt.addRow('High-Pass', self.hpEdit)
        filt.addRow('Low-Pass', self.lpEdit)

        applyform = QFormLayout()
        applyform.addRow('Scaling', self.scaleEdit)
        applyform.addRow(applyButton)

        reflayout = QVBoxLayout()
        reflayout.addWidget(self.l1)
        reflayout.addWidget(rerefButton)

        layout = QGridLayout()
        layout.addWidget(self.list_grp, 0, 0)
        layout.addLayout(hdr, 0, 1)
        layout.addWidget(QLabel('Channels to Visualize'), 1, 0)
        layout.addWidget(QLabel('Reference Channels'), 1, 1)
        layout.addWidget(self.l0, 2, 0)
        layout.addLayout(reflayout, 2, 1)
        layout.addLayout(filt, 3, 0)
        layout.addLayout(applyform, 3, 1)

        self.setLayout(layout)
        self.layout = layout
        self.update_list_grp()

    def update_list_grp(self):
        """Update the list containing the channels."""
        current = self.list_grp.currentText()
        idx = [x['name'] for x in self.groups].index(current)
        self.highlight_list(self.l0, self.groups[idx]['chan_to_plot'])
        self.highlight_list(self.l1, self.groups[idx]['ref_chan'])
        self.hpEdit.setText(str(self.groups[idx]['filter']['low_cut']))
        self.lpEdit.setText(str(self.groups[idx]['filter']['high_cut']))
        self.scaleEdit.setText(str(self.groups[idx]['scale']))
        self.current = current  # update index

    def create_list(self, l):
        """Create list of channels (one for those to plot, one for ref).

        Parameters
        ----------
        l : instance of QListWidget
            one of the two lists (chan_to_plot or ref_chan)

        """
        ExtendedSelection = QAbstractItemView.SelectionMode(3)
        l.setSelectionMode(ExtendedSelection)
        for chan in self.chan_name:
            item = QListWidgetItem(chan)
            l.addItem(item)

    def highlight_list(self, l, selected_chan):
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
        selectedItems = self.l0.selectedItems()
        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())
        self.highlight_list(self.l1, chan_to_plot)

    def update_chan_grp(self):
        """Read the GUI and update the channel groups."""
        selectedItems = self.l0.selectedItems()
        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())

        selectedItems = self.l1.selectedItems()
        ref_chan = []
        for selected in selectedItems:
            ref_chan.append(selected.text())

        hp = self.hpEdit.text()
        if hp == 'None':
            low_cut = None
        else:
            low_cut = float(hp)

        lp = self.lpEdit.text()
        if lp == 'None':
            high_cut = None
        else:
            high_cut = float(lp)

        scale = self.scaleEdit.text()

        idx = [x['name'] for x in self.groups].index(self.current)
        self.groups[idx]['chan_to_plot'] = chan_to_plot
        self.groups[idx]['ref_chan'] = ref_chan
        self.groups[idx]['filter']['low_cut'] = low_cut
        self.groups[idx]['filter']['high_cut'] = high_cut
        self.groups[idx]['scale'] = float(scale)

        self.update_list_grp()

    def apply_changes(self):
        """Apply changes to the plots."""
        self.update_chan_grp()
        self.parent.overview.update_position()
        self.parent.spectrum.update_spectrum()

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
        new_grp_name = self.inputdialog.textValue()
        self.groups.append({'name': new_grp_name,
                              'chan_to_plot': [],
                              'ref_chan': [],
                              'color': QColor('black'),
                              'filter': {'low_cut': None, 'high_cut': None},
                              'scale': 1})
        idx = self.list_grp.currentIndex()
        self.list_grp.insertItem(idx + 1, new_grp_name)
        self.list_grp.setCurrentIndex(idx + 1)
        self.update_list_grp()

    def rename_group(self):
        """Rename a group of channels."""

        new_grp_name = self.inputdialog.textValue()
        idx = [x['name'] for x in self.groups].index(self.current)
        self.groups[idx]['name'] = new_grp_name
        self.current = new_grp_name

        idx = self.list_grp.currentIndex()
        self.list_grp.setItemText(idx, new_grp_name)

    def color_group(self):
        """Change color to a group of channels.

        """
        idx = [x['name'] for x in self.groups].index(self.current)
        newcolor = QColorDialog.getColor(self.groups[idx]['color'])
        self.groups[idx]['color'] = newcolor

    def delete_group(self):
        """Delete one group of channels.

        TODO: how to deal when it's the last one?

        """
        idx = self.list_grp.currentIndex()
        self.list_grp.removeItem(idx)
        self.groups.pop(idx)
        self.update_list_grp()
