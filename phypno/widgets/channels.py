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
                      },
                      ]

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

        self.hpEdit = QLineEdit('')
        self.lpEdit = QLineEdit('')

        applyButton = QPushButton('Apply')
        applyButton.clicked.connect(self.apply_changes)

        self.list_grp = QComboBox()
        for one_grp in self.groups:
            self.list_grp.addItem(one_grp['name'])

        self.list_grp.activated.connect(self.update_chan_grp)
        self.current = self.list_grp.currentText()

        hdr = QGridLayout()
        hdr.addWidget(addButton, 0, 0)
        hdr.addWidget(renameButton, 0, 1)
        hdr.addWidget(colorButton, 1, 0)
        hdr.addWidget(delButton, 1, 1)

        filt = QFormLayout()
        filt.addRow('High-Pass', self.hpEdit)
        filt.addRow('Low-Pass', self.lpEdit)

        layout = QGridLayout()
        layout.addWidget(self.list_grp, 0, 0)
        layout.addLayout(hdr, 0, 1)
        layout.addWidget(QLabel('Channels to Visualize'), 1, 0)
        layout.addWidget(QLabel('Reference Channels'), 1, 1)
        layout.addLayout(filt, 3, 0)
        layout.addWidget(applyButton, 3, 1)

        self.setLayout(layout)
        self.layout = layout
        self.update_list_grp()

    def update_list_grp(self):
        """Update the list containing the channels.

        TODO: this should probably update the filter settings.

        """
        current = self.list_grp.currentText()
        idx = [x['name'] for x in self.groups].index(current)
        l0 = self.create_list(self.groups[idx]['chan_to_plot'])
        l1 = self.create_list(self.groups[idx]['ref_chan'])
        self.layout.addWidget(l0, 2, 0)
        self.layout.addWidget(l1, 2, 1)
        self.l0 = l0
        self.l1 = l1
        self.current = current  # update index

    def create_list(self, selected_chan):
        """Create list of channels (one for those to plot, one for ref).

        Parameters
        ----------
        selected_chan : list of str
            channels to indicate as selected.

        """
        l = QListWidget()
        ExtendedSelection = QAbstractItemView.SelectionMode(3)
        l.setSelectionMode(ExtendedSelection)
        for chan in self.chan_name:
            item = QListWidgetItem(chan)
            l.addItem(item)
            if chan in selected_chan:
                item.setSelected(True)
            else:
                item.setSelected(False)
        return l

    def update_chan_grp(self):
        """Read the GUI and update the channel groups.

        """
        selectedItems = self.l0.selectedItems()
        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())

        selectedItems = self.l1.selectedItems()
        ref_chan = []
        for selected in selectedItems:
            ref_chan.append(selected.text())

        hp = self.hpEdit.text()
        if hp == '':
            low_cut = None
        else:
            low_cut = float(hp)

        lp = self.lpEdit.text()
        if lp == '':
            high_cut = None
        else:
            high_cut = float(lp)

        idx = [x['name'] for x in self.groups].index(self.current)
        self.groups[idx]['chan_to_plot'] = chan_to_plot
        self.groups[idx]['ref_chan'] = ref_chan
        self.groups[idx]['filter']['low_cut'] = low_cut
        self.groups[idx]['filter']['high_cut'] = high_cut

        self.update_list_grp()

    def apply_changes(self):
        """Apply changes to the plots.

        """
        self.update_chan_grp()
        self.parent.overview.update_position()

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
        """Create a new group of channels.

        """
        new_grp_name = self.inputdialog.textValue()
        self.groups.append({'name': new_grp_name,
                              'chan_to_plot': [],
                              'ref_chan': [],
                              'color': QColor('black'),
                              'filter': {'low_cut': None, 'high_cut': None},
                              })
        idx = self.list_grp.currentIndex()
        self.list_grp.insertItem(idx + 1, new_grp_name)
        self.list_grp.setCurrentIndex(idx + 1)
        self.update_list_grp()

    def rename_group(self):
        """Rename a group of channels.

        """
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
