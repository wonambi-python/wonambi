"""Widget to define channels, montage and filters.
"""
from copy import deepcopy
from json import dump, load
from logging import getLogger
from os.path import splitext

from PyQt5.QtGui import (QColor,
                         )

from PyQt5.QtWidgets import (QAbstractItemView,
                             QAction,
                             QColorDialog,
                             QDoubleSpinBox,
                             QFileDialog,
                             QFormLayout,
                             QGridLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QInputDialog,
                             QLabel,
                             QListWidget,
                             QListWidgetItem,
                             QPushButton,
                             QVBoxLayout,
                             QTabWidget,
                             QWidget
                             )


from .settings import Config
from .utils import FormFloat, FormStr

lg = getLogger(__name__)


class ConfigChannels(Config):
    """Widget with preferences in Settings window for Channels."""
    def __init__(self, update_widget):
        super().__init__('channels', update_widget)

    def create_config(self):
        box0 = QGroupBox('Channels')

        self.index['hp'] = FormFloat()
        self.index['lp'] = FormFloat()
        self.index['color'] = FormStr()
        self.index['scale'] = FormFloat()

        form_layout = QFormLayout()
        form_layout.addRow('Default High-Pass Filter', self.index['hp'])
        form_layout.addRow('Default Low-Pass Filter', self.index['lp'])
        form_layout.addRow('Default Color', self.index['color'])
        form_layout.addRow('Default Scale', self.index['scale'])
        box0.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


class ChannelsGroup(QWidget):
    """Tab inside the Channels widget.

    Parameters
    ----------
    chan_name : list of str
        list of all the channels in the dataset
    config_value : dict
        default values for the channels
    s_freq : int
        sampling frequency (to define max of filter)

    Attributes
    ----------
    chan_name : list of str
        list of all the channels in the dataset

    idx_l0 : QListWidget
        list with the channels to plot
    idx_l1 : QListWidget
        list with the channels to use as reference
    idx_hp : QDoubleSpinBox
        spin box to indicate the high-pass filter
    idx_lp : QDoubleSpinBox
        spin box to indicate the low-pass filter
    idx_scale : QDoubleSpinBox
        spin_box to indicate the group-specific scaling
    idx_reref : QPushButton
        it triggers a selection of reference channels equal to the channels to
        plot.
    idx_color : QColor
        color of the traces beloning to this channel group (it could be a
        property of QWidget)

    Notes
    -----
    TODO: re-referencing should be more flexible, by allowing other types of
    referencing.

    Use config_value instead of config, because it's easier to pass dict
    when loading channels montage.
    """
    def __init__(self, chan_name, group_name, config_value, s_freq):
        super().__init__()

        self.chan_name = chan_name
        self.group_name = group_name

        self.idx_l0 = QListWidget()
        self.idx_l1 = QListWidget()

        self.add_channels_to_list(self.idx_l0)
        self.add_channels_to_list(self.idx_l1)

        self.idx_hp = QDoubleSpinBox()
        hp = config_value['hp']
        if hp is None:
            hp = 0
        self.idx_hp.setValue(hp)
        self.idx_hp.setSuffix(' Hz')
        self.idx_hp.setDecimals(1)
        self.idx_hp.setMaximum(s_freq / 2)
        self.idx_hp.setToolTip('0 means no filter')

        self.idx_lp = QDoubleSpinBox()
        lp = config_value['lp']
        if lp is None:
            lp = 0
        self.idx_lp.setValue(lp)
        self.idx_lp.setSuffix(' Hz')
        self.idx_lp.setDecimals(1)
        self.idx_lp.setMaximum(s_freq / 2)
        self.idx_lp.setToolTip('0 means no filter')

        self.idx_scale = QDoubleSpinBox()
        self.idx_scale.setValue(config_value['scale'])
        self.idx_scale.setSuffix('x')

        self.idx_reref = QPushButton('Average')
        self.idx_reref.clicked.connect(self.rereference)

        self.idx_color = QColor(config_value['color'])

        l_form = QFormLayout()
        l_form.addRow('High-Pass', self.idx_hp)
        l_form.addRow('Low-Pass', self.idx_lp)

        r_form = QFormLayout()
        r_form.addRow('Scaling', self.idx_scale)
        r_form.addRow('Reference', self.idx_reref)

        l0_layout = QVBoxLayout()
        l0_layout.addWidget(QLabel('Active'))
        l0_layout.addWidget(self.idx_l0)

        l1_layout = QVBoxLayout()
        l1_layout.addWidget(QLabel('Reference'))
        l1_layout.addWidget(self.idx_l1)

        l_layout = QHBoxLayout()
        l_layout.addLayout(l0_layout)
        l_layout.addLayout(l1_layout)

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

        l.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
        """Automatically highlight channels to use as reference, based on
        selected channels."""
        selectedItems = self.idx_l0.selectedItems()

        chan_to_plot = []
        for selected in selectedItems:
            chan_to_plot.append(selected.text())
        self.highlight_channels(self.idx_l1, chan_to_plot)

    def get_info(self):
        """Get the information about the channel groups.

        Returns
        -------
        dict
            information about this channel group

        Notes
        -----
        The items in selectedItems() are ordered based on the user's selection
        (which appears pretty random). It's more consistent to use the same
        order of the main channel list. That's why the additional for-loop
        is necessary. We don't care about the order of the reference channels.
        """
        selectedItems = self.idx_l0.selectedItems()
        selected_chan = [x.text() for x in selectedItems]
        chan_to_plot = []
        for chan in self.chan_name:
            if chan in selected_chan:
                chan_to_plot.append(chan)

        selectedItems = self.idx_l1.selectedItems()
        ref_chan = []
        for selected in selectedItems:
            ref_chan.append(selected.text())

        hp = self.idx_hp.value()
        if hp == 0:
            low_cut = None
        else:
            low_cut = hp

        lp = self.idx_lp.value()
        if lp == 0:
            high_cut = None
        else:
            high_cut = lp

        scale = self.idx_scale.value()

        group_info = {'name': self.group_name,
                      'chan_to_plot': chan_to_plot,
                      'ref_chan': ref_chan,
                      'hp': low_cut,
                      'lp': high_cut,
                      'scale': float(scale),
                      'color': self.idx_color
                      }

        return group_info


class Channels(QWidget):
    """Widget with information about channel groups.

    Attributes
    ----------
    parent : QMainWindow
        the main window
    config : ConfigChannels
        preferences for this widget

    filename : path to file
        file with the channel groups
    groups : list of dict
        each dict contains information about one channel group

    tabs : QTabWidget
        Widget that contains the tabs with channel groups
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigChannels(lambda: None)

        self.filename = None
        self.groups = []

        self.tabs = None

        self.create()
        self.create_action()

    def create(self):
        """Create Channels Widget"""
        add_button = QPushButton('New')
        add_button.clicked.connect(self.new_group)
        color_button = QPushButton('Color')
        color_button.clicked.connect(self.color_group)
        del_button = QPushButton('Delete')
        del_button.clicked.connect(self.del_group)
        apply_button = QPushButton('Apply')
        apply_button.clicked.connect(self.apply)

        self.button_add = add_button
        self.button_color = color_button
        self.button_del = del_button
        self.button_apply = apply_button

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

        self.setEnabled(False)
        self.button_color.setEnabled(False)
        self.button_del.setEnabled(False)
        self.button_apply.setEnabled(False)

    def create_action(self):
        """Create actions related to channel selection."""
        actions = {}

        act = QAction('Load Montage...', self)
        act.triggered.connect(self.load_channels)
        act.setEnabled(False)
        actions['load_channels'] = act

        act = QAction('Save Montage...', self)
        act.triggered.connect(self.save_channels)
        act.setEnabled(False)
        actions['save_channels'] = act

        self.action = actions

    def update(self):
        self.setEnabled(True)
        self.action['load_channels'].setEnabled(True)
        self.action['save_channels'].setEnabled(True)

    def new_group(self, checked=False, test_name=None):
        """Create a new channel group.

        Parameters
        ----------
        checked : bool
            comes from QAbstractButton.clicked
        test_name : str
            used for testing purposes to avoid modal window

        Notes
        -----
        Don't call self.apply() just yet, only if the user wants it.
        """
        chan_name = self.parent.labels.chan_name
        if chan_name is None:
            msg = 'No dataset loaded'
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)

        else:
            if test_name is None:
                new_name = QInputDialog.getText(self, 'New Channel Group',
                                                'Enter Name')
            else:
                new_name = [test_name, True]  # like output of getText

            if new_name[1]:
                s_freq = self.parent.info.dataset.header['s_freq']
                group = ChannelsGroup(chan_name, new_name[0],
                                      self.config.value, s_freq)
                self.tabs.addTab(group, new_name[0])
                self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)

                # activate buttons
                self.button_color.setEnabled(True)
                self.button_del.setEnabled(True)
                self.button_apply.setEnabled(True)

    def color_group(self, checked=False, test_color=None):
        """Change the color of the group."""
        group = self.tabs.currentWidget()
        if test_color is None:
            newcolor = QColorDialog.getColor(group.idx_color)
        else:
            newcolor = test_color
        group.idx_color = newcolor

        self.apply()

    def del_group(self):
        """Delete current group."""
        idx = self.tabs.currentIndex()
        self.tabs.removeTab(idx)

        self.apply()

    def apply(self):
        """Apply changes to the plots."""
        self.read_group_info()

        if self.tabs.count() == 0:
            # disactivate buttons
            self.button_color.setEnabled(False)
            self.button_del.setEnabled(False)
            self.button_apply.setEnabled(False)
        else:
            # activate buttons
            self.button_color.setEnabled(True)
            self.button_del.setEnabled(True)
            self.button_apply.setEnabled(True)

        if self.groups:
            self.parent.overview.update_position()
            self.parent.spectrum.update()
            self.parent.notes.enable_events()
        else:
            self.parent.traces.reset()
            self.parent.spectrum.reset()
            self.parent.notes.enable_events()

    def read_group_info(self):
        """Get information about groups directly from the widget."""
        self.groups = []
        for i in range(self.tabs.count()):
            one_group = self.tabs.widget(i).get_info()
            # one_group['name'] = self.tabs.tabText(i)
            self.groups.append(one_group)

    def load_channels(self, checked=False, test_name=None):
        """Load channel groups from file.

        Parameters
        ----------
        test_name : path to file
            when debugging the function, you can open a channels file from the
            command line
        """
        chan_name = self.parent.labels.chan_name

        if self.filename is not None:
            filename = self.filename
        elif self.parent.info.filename is not None:
            filename = (splitext(self.parent.info.filename)[0] +
                        '_channels.json')
        else:
            filename = None

        if test_name is None:
            filename, _ = QFileDialog.getOpenFileName(self,
                                                      'Open Channels Montage',
                                                      filename,
                                                      'Channels File (*.json)')
        else:
            filename = test_name

        if filename == '':
            return

        self.filename = filename
        with open(filename, 'r') as outfile:
            groups = load(outfile)

        s_freq = self.parent.info.dataset.header['s_freq']
        no_in_dataset = []
        for one_grp in groups:
            no_in_dataset.extend(set(one_grp['chan_to_plot']) -
                                 set(chan_name))
            chan_to_plot = set(chan_name) & set(one_grp['chan_to_plot'])
            ref_chan = set(chan_name) & set(one_grp['ref_chan'])

            group = ChannelsGroup(chan_name, one_grp['name'], one_grp, s_freq)
            group.highlight_channels(group.idx_l0, chan_to_plot)
            group.highlight_channels(group.idx_l1, ref_chan)
            self.tabs.addTab(group, one_grp['name'])

        if no_in_dataset:
            msg = 'Channels not present in the dataset: ' + ', '.join(no_in_dataset)
            self.parent.statusBar().showMessage(msg)
            lg.debug(msg)

        self.apply()

    def save_channels(self, checked=False, test_name=None):
        """Save channel groups to file."""
        self.read_group_info()

        if self.filename is not None:
            filename = self.filename
        elif self.parent.info.filename is not None:
            filename = (splitext(self.parent.info.filename)[0] +
                        '_channels.json')
        else:
            filename = None

        if test_name is None:
            filename, _ = QFileDialog.getSaveFileName(self,
                                                      'Save Channels Montage',
                                                      filename,
                                                      'Channels File (*.json)')
        else:
            filename = test_name

        if filename == '':
            return

        self.filename = filename

        groups = deepcopy(self.groups)
        for one_grp in groups:
            one_grp['color'] = one_grp['color'].rgba()

        with open(filename, 'w') as outfile:
            dump(groups, outfile, indent=' ')

    def reset(self):
        """Reset all the information of this widget."""
        self.filename = None
        self.groups = []

        self.tabs.clear()

        self.setEnabled(False)
        self.button_color.setEnabled(False)
        self.button_del.setEnabled(False)
        self.button_apply.setEnabled(False)
        self.action['load_channels'].setEnabled(False)
        self.action['save_channels'].setEnabled(False)
