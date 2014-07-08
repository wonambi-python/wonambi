"""Large and simple widget to indicate settings/preferences.

"""
from logging import getLogger
lg = getLogger(__name__)

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import (QDialog,
                         QFormLayout,
                         QGroupBox,
                         QHBoxLayout,
                         QLineEdit,
                         QPushButton,
                         QVBoxLayout,
                         )

config = QSettings("phypno", "scroll_data")

DEFAULTS = {'main/geometry': [400, 300, 1024, 768],
            'main/hidden_docks': ['Video'],
            'main/recording_dir': '/home/gio/recordings',
            'overview/window_start': 0,
            'overview/window_length': 30,
            'overview/window_length_presets': [1, 5, 10, 20, 30, 60],
            'overview/window_step': 5,
            'overview/timestamp_steps': 60 * 60,
            'traces/n_time_labels': 3,
            'traces/y_distance': 50.,
            'traces/y_distance_presets': [20, 30, 40, 50, 100, 200],
            'traces/y_scale': 1.,
            'traces/y_scale_presets': [.1, .2, .5, 1, 2, 5, 10],
            'traces/label_ratio': 0.05,
            'utils/read_intervals': 10 * 60,
            'stages/scoring_window': 30,
            'detect/spindle_method': 'UCSD',
            'spectrum/x_limit': [0, 30],
            'spectrum/y_limit': [-5, 5],
            'video/vlc_size': '640x480',
            'video/vlc_exe': 'C:/Program Files (x86)/VideoLAN/VLC/vlc.exe',
            }

# Read/write default values using QSettings
for key, value in DEFAULTS.items():
    type_value = type(value)
    config_value = config.value(key)
    if config_value is not None:
        if type_value is list:
            DEFAULTS[key] = eval(config_value)
        else:
            DEFAULTS[key] = type_value(config_value)


class Preferences(QDialog):
    """Dialog which contains the preferences/settings.

    Attributes
    ----------
    parent : instance of QMainWindow
        The main window.
    values : dict
        Values of the preferences in key/value format.
    idx_edits : dict of instances of QLineEdit
        Values as QLineEdit for each preference value.

    """
    def __init__(self, parent):
        lg.debug('make preferences')
        super().__init__()
        self.parent = parent

        self.values = DEFAULTS

        self.idx_edits = {}

        self.create_preferences()

    def create_preferences(self):
        """Create the widgets containing the QLineEdit."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        group = {}
        group_layout = {}
        widgets = set([x.split('/')[0] for x in DEFAULTS])

        # It creates a QGroupBox with QFormLayout for each widget
        for one_widget in sorted(widgets):
            lg.debug('Adding preferences for ' + one_widget + ' widget')
            group[one_widget] = QGroupBox(one_widget)
            group_layout[one_widget] = QFormLayout()
            group[one_widget].setLayout(group_layout[one_widget])
            layout.addWidget(group[one_widget])

        # It adds row to a widget's QGroupBox
        for widget_key in sorted(DEFAULTS):
            one_widget, key = widget_key.split('/')
            edit = QLineEdit('')
            group_layout[one_widget].addRow(key, edit)
            self.idx_edits[widget_key] = edit

        ok_button = QPushButton('OK')
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.save_values)

        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def update_preferences(self):
        """Call directly display_preferences.

        Notes
        -----
        Usually, self.values should be None and values are updated here but in
        the case of preferences they should be available as soon as the
        widgets are created.

        """
        self.display_preferences()

    def display_preferences(self):
        """Display the preferences."""
        for widget_key, value in DEFAULTS.items():
            lg.debug('Setting {} to {}'.format(widget_key, value))
            self.idx_edits[widget_key].setText(str(value))

    def save_values(self):
        """Save edited values into QSettings file.

        Notes
        -----
        TODO: depending on the edit, update the figure.

        """
        for key, one_edit in self.idx_edits.items():
            text = one_edit.text()
            if text != self.values[key]:
                lg.info('Value has been modified: ' +
                        '{} -> {}'.format(self.values[key], text))
                self.values[key] = text
                config.setValue(key, text)

        self.accept()
