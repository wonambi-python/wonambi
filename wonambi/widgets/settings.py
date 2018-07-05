"""Large and simple widget to indicate settings/Settings.
"""
from logging import getLogger

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFormLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QListWidget,
                             QSplitter,
                             QStackedWidget,
                             QTextEdit,
                             QVBoxLayout,
                             QWidget,
                             )

from .utils import FormInt, FormList, FormStr

lg = getLogger(__name__)

settings = QSettings("wonambi", "scroll_data")


# DO NOT DUPLICATE NAMES
DEFAULTS = {}
DEFAULTS['channels'] = {'hp': .5,
                        'lp': 45,
                        'color': 'black',
                        'scale': 1,
                        }
DEFAULTS['overview'] = {'timestamp_steps': 60 * 60,
                        'overview_scale': 30,
                        }
DEFAULTS['spectrum'] = {'x_min': 0.,
                        'x_max': 30.,
                        'x_tick': 10.,
                        'y_min': -5.,
                        'y_max': 5.,
                        'y_tick': 5.,
                        'log': True,
                        }
DEFAULTS['notes'] = {'marker_show': True,
                     'marker_color': 'darkBlue',
                     'annot_show': True,
                     'annot_bookmark_color': 'darkMagenta',
                     'min_marker_dur': .1,
                     'min_marker_display_dur': .1,
                     'scoring_window': 30,
                     }
DEFAULTS['traces'] = {'n_time_labels': 3,
                      'y_distance': 50.,
                      'y_scale': 1.,
                      'label_ratio': 0.05,
                      'max_s_freq': 30000,
                      'window_start': 0,
                      'window_length': 30,
                      'window_step': 5,
                      'grid_x': True,
                      'grid_xtick': 1,  # in seconds
                      'grid_y': True,
                      'grid_ytick': 35,
                      }
DEFAULTS['settings'] = {'max_dataset_history': 20,
                        'y_distance_presets': [20., 30., 40., 50., 100., 200.],
                        'y_scale_presets': [.1, .2, .5, 1, 2, 5, 10],
                        'window_length_presets': [1., 5., 10., 20., 30., 60.],
                        'recording_dir': '/home/gio/recordings',
                        }
DEFAULTS['video'] = {}


class Settings(QDialog):
    """Window showing the Settings/settings.

    Parameters
    ----------
    parent : instance of QMainWindow
        the main window
    """
    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent
        self.config = ConfigUtils(self.parent.refresh)

        self.setWindowTitle('Settings')
        self.create_settings()

    def create_settings(self):
        """Create the widget, organized in two parts.

        Notes
        -----
        When you add widgets in config, remember to update show_settings too
        """
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply |
                                QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_apply = bbox.button(QDialogButtonBox.Apply)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)
        bbox.clicked.connect(self.button_clicked)

        page_list = QListWidget()
        page_list.setSpacing(1)
        page_list.currentRowChanged.connect(self.change_widget)

        pages = ['General', 'Overview', 'Signals', 'Channels', 'Spectrum',
                 'Notes', 'Video']
        for one_page in pages:
            page_list.addItem(one_page)

        self.stacked = QStackedWidget()
        self.stacked.addWidget(self.config)
        self.stacked.addWidget(self.parent.overview.config)
        self.stacked.addWidget(self.parent.traces.config)
        self.stacked.addWidget(self.parent.channels.config)
        self.stacked.addWidget(self.parent.spectrum.config)
        self.stacked.addWidget(self.parent.notes.config)
        self.stacked.addWidget(self.parent.video.config)

        hsplitter = QSplitter()
        hsplitter.addWidget(page_list)
        hsplitter.addWidget(self.stacked)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

    def change_widget(self, new_row):
        """Change the widget on the right side.

        Parameters
        ----------
        new_row : int
            index of the widgets
        """
        self.stacked.setCurrentIndex(new_row)

    def button_clicked(self, button):
        """Action when button was clicked.

        Parameters
        ----------
        button : instance of QPushButton
            which button was pressed
        """
        if button in (self.idx_ok, self.idx_apply):

            # loop over widgets, to see if they were modified
            for i_config in range(self.stacked.count()):
                one_config = self.stacked.widget(i_config)

                if one_config.modified:
                    lg.debug('Settings for ' + one_config.widget +
                             ' were modified')
                    one_config.get_values()

                    if self.parent.info.dataset is not None:
                        one_config.update_widget()
                    one_config.modified = False

            if button == self.idx_ok:
                self.accept()

        if button == self.idx_cancel:
            self.reject()


class Config(QWidget):
    """Base class for widgets used in the Settings.

    Parameters
    ----------
    widget : str
        name of the widget
    update_widget : function
        function to run to update the main window with new values

    Attributes
    ----------
    modified : bool
        if the preference widget has been changed
    value : dict
        dictionary with the actual current values
    index : dict
        dictionary with the instances of the small widgets

    Notes
    -----
    You'll need to implement create_config with the QGroupBox and layouts
    """
    def __init__(self, widget, update_widget):
        super().__init__()

        self.modified = False
        self.widget = widget

        value_names = list(DEFAULTS[widget].keys())
        self.value = self.create_values(value_names)
        self.index = self.create_indices(value_names)

        self.create_config()
        self.put_values()
        self.update_widget = update_widget

    def create_values(self, value_names):
        """Read original values from the settings or the defaults.

        Parameters
        ----------
        value_names : list of str
            list of value names to read

        Returns
        -------
        dict
            dictionary with the value names as keys
        """
        output = {}
        for value_name in value_names:
            output[value_name] = read_settings(self.widget, value_name)

        return output

    def create_indices(self, value_names):
        """Create empty indices as None. They'll be created by create_config.

        """
        return dict(zip(value_names, [None] * len(value_names)))

    def get_values(self):
        """Get values from the GUI and save them in preference file."""
        for value_name, widget in self.index.items():
            self.value[value_name] = widget.get_value(self.value[value_name])

            setting_name = self.widget + '/' + value_name
            settings.setValue(setting_name, self.value[value_name])

    def put_values(self):
        """Put values to the GUI.

        Notes
        -----
        In addition, when one small widget has been changed, it calls
        set_modified, so that we know that the preference widget was modified.

        """
        for value_name, widget in self.index.items():
            widget.set_value(self.value[value_name])
            widget.connect(self.set_modified)

    def create_config(self):
        """Placeholder: it'll be replaced with actual layout."""
        pass

    def set_modified(self):
        """Simply mark that the preference widget was modified.

        Notes
        -----
        You cannot use lambda because they don't accept assignments.

        """
        self.modified = True


class ConfigUtils(Config):

    def __init__(self, update_widget):
        super().__init__('settings', update_widget)

    def create_config(self):

        box0 = QGroupBox('History')
        self.index['max_dataset_history'] = FormInt()
        self.index['recording_dir'] = FormStr()

        form_layout = QFormLayout()
        form_layout.addRow('Max History Size',
                           self.index['max_dataset_history'])
        form_layout.addRow('Directory with recordings',
                           self.index['recording_dir'])
        box0.setLayout(form_layout)

        box1 = QGroupBox('Default values')
        self.index['y_distance_presets'] = FormList()
        self.index['y_scale_presets'] = FormList()
        self.index['window_length_presets'] = FormList()

        form_layout = QFormLayout()
        form_layout.addRow('Signal scaling, presets',
                           self.index['y_scale_presets'])
        form_layout.addRow('Distance between signals, presets',
                           self.index['y_distance_presets'])
        form_layout.addRow('Window length, presets',
                           self.index['window_length_presets'])
        box1.setLayout(form_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addWidget(box1)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


def read_settings(widget, value_name):
    """Read Settings information, either from INI or from default values.

    Parameters
    ----------
    widget : str
        name of the widget
    value_name : str
        name of the value of interest.

    Returns
    -------
    multiple types
        type depends on the type in the default values.

    """
    setting_name = widget + '/' + value_name
    default_value = DEFAULTS[widget][value_name]

    default_type = type(default_value)
    if default_type is list:
        default_type = type(default_value[0])

    val = settings.value(setting_name, default_value, type=default_type)
    return val


class HelpDialog(QDialog):
    """Generic help dialog, showing uneditable HTML text."""
    def __init__(self):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.setWindowTitle('Help')
        self.setWindowModality(Qt.ApplicationModal)

        self.create_dialog()

    def create_dialog(self):
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        bbox.clicked.connect(self.accept)

        textbox = QTextEdit(self)
        textbox.setReadOnly(True)
        self.textbox = textbox

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(textbox)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

    def set_text(self, message):
        """Insert HTML text."""
        self.textbox.insertHtml(message)
