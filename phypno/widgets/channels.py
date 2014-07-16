"""Widget to define channels, montage and filters.

"""
from logging import getLogger
lg = getLogger(__name__)

from PyQt4.QtGui import (QAbstractItemView,
                         QColor,
                         QColorDialog,
                         QFormLayout,
                         QGridLayout,
                         QGroupBox,
                         QHBoxLayout,
                         QInputDialog,
                         QLineEdit,
                         QListWidget,
                         QListWidgetItem,
                         QPushButton,
                         QVBoxLayout,
                         QTabWidget,
                         QWidget
                         )


from .settings import Config, FormFloat, FormStr


EMPTY_FILTER = ('None', '', 'none', '0')


class ConfigChannels(Config):

    def __init__(self, update_widget):
        super().__init__('channels', update_widget)

    def create_config(self):

        box0 = QGroupBox('Channels')

        self.index['hp'] = FormFloat()
        self.index['lp'] = FormFloat()
        self.index['color'] = FormStr()

        form_layout = QFormLayout()
        form_layout.addRow('Default High-Pass Filter', self.index['hp'])
        form_layout.addRow('Default Low-Pass Filter', self.index['lp'])
        form_layout.addRow('Default Color', self.index['color'])
        box0.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


class ChannelsGroup(QWidget):
    def __init__(self, chan_name, config):
        super().__init__()

        self.chan_name = chan_name

        self.setProperty('color', QColor(config.value['color']))

        self.idx_l0 = QListWidget()
        self.idx_l1 = QListWidget()

        self.add_channels_to_list(self.idx_l0)
        self.add_channels_to_list(self.idx_l1)

        self.idx_hp = QLineEdit(str(config.value['hp']))
        self.idx_lp = QLineEdit(str(config.value['lp']))
        self.idx_scale = QLineEdit('1')
        self.idx_reref = QPushButton('Average')  # TODO: actually combobox
        self.idx_reref.clicked.connect(self.rereference)

        l_form = QFormLayout()
        l_form.addRow('High-Pass', self.idx_hp)
        l_form.addRow('Low-Pass', self.idx_lp)

        r_form = QFormLayout()
        r_form.addRow('Scaling', self.idx_scale)
        r_form.addRow('Reference', self.idx_reref)

        l_layout = QHBoxLayout()
        l_layout.addWidget(self.idx_l0)
        l_layout.addWidget(self.idx_l1)

        lr_form = QHBoxLayout()
        lr_form.addLayout(l_form)
        lr_form.addLayout(r_form)

        layout = QVBoxLayout()
        layout.addLayout(l_layout)
        layout.addLayout(lr_form)

        self.setLayout(layout)

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

    def rereference(self):
        #TODO: only reference to average
        selectedItems = self.idx_l0.selectedItems()

        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())
        self.highlight_channels(self.idx_l1, chan_to_plot)

    def get_info(self):
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

        group_info = {'name': '',  # not present in widget
                      'chan_to_plot': chan_to_plot,
                      'ref_chan': ref_chan,
                      'filter': {'low_cut': low_cut, 'high_cut': high_cut},
                      'scale': float(scale),
                      'color': self.property('color')
                      }

        return group_info


class Channels(QWidget):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigChannels(lambda: None)

        self.groups = []
        self.chan_name = []

        self.tabs = None

        self.create_channels()

    def create_channels(self):

        add_button = QPushButton('New')
        add_button.clicked.connect(self.new_group)
        color_button = QPushButton('Color')
        color_button.clicked.connect(self.color_group)
        del_button = QPushButton('Delete')
        del_button.clicked.connect(self.del_group)
        apply_button = QPushButton('Apply')
        apply_button.clicked.connect(self.apply)

        buttons = QGridLayout()
        buttons.addWidget(add_button, 0, 0)
        buttons.addWidget(color_button, 1, 0)
        buttons.addWidget(del_button, 0, 1)
        buttons.addWidget(apply_button, 1, 1)

        self.tabs = QTabWidget()

        layout = QVBoxLayout()
        layout.addLayout(buttons)
        layout.addWidget(self.tabs)

        self.setLayout(layout)

    def new_group(self):
        if self.chan_name is None:
            self.parent.statusBar().showMessage('No dataset loaded')
        else:
            new_name = QInputDialog.getText(self, 'New Channel Group',
                                            'Enter Name')
            if new_name[1]:
                group = ChannelsGroup(self.chan_name, self.config)
                self.tabs.addTab(group, new_name[0])
                self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)

                self.apply()

    def color_group(self):
        group = self.tabs.currentWidget()
        newcolor = QColorDialog.getColor(group.property('color'))
        group.setProperty('color', newcolor)

        self.apply()

    def del_group(self):
        idx = self.tabs.currentIndex()
        self.tabs.removeTab(idx)

        self.apply()

    def apply(self):
        """Apply changes to the plots."""
        self.read_group_info()
        self.parent.spectrum.update_spectrum()
        self.parent.overview.update_position()

    def read_group_info(self):
        self.groups = []
        for i in range(self.tabs.count()):
            one_group = self.tabs.widget(i).get_info()
            one_group['name'] = self.tabs.tabText(i)
            self.groups.append(one_group)

    def update(self, chan_name):
        """Read the channels and updates the widget.

        Parameters
        ----------
        chan_name : list of str
            list of channels, to choose from.

        """
        self.chan_name = chan_name

    def reset(self):
        self.chan_name = []
        self.groups = []
        self.tabs.clear()
