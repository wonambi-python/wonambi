"""Large and simple widget to indicate settings/preferences.

"""
from logging import getLogger
lg = getLogger(__name__)

from ast import literal_eval

from PyQt4.QtCore import QSettings, Qt
from PyQt4.QtGui import (QCheckBox,
                         QDialogButtonBox,
                         QDialog,
                         QHBoxLayout,
                         QLineEdit,
                         QListWidget,
                         QSplitter,
                         QStackedWidget,
                         QVBoxLayout,
                         QWidget,
                         )


settings = QSettings("phypno", "scroll_data")

DEFAULTS = {}
DEFAULTS['detect'] = {'spindle_method': 'UCSD',
                      }

DEFAULTS['overview'] = {'window_start': 0,
                        'window_length': 30,
                        'window_step': 5,
                        'timestamp_steps': 60 * 60,
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
DEFAULTS['stages'] = {'scoring_window': 30,
                      }
DEFAULTS['traces'] = {'n_time_labels': 3,
                      'y_distance': 50.,
                      'y_scale': 1.,
                      'label_ratio': 0.05,
                      }
DEFAULTS['utils'] = {'window_x': 400,
                     'window_y': 200,
                     'window_width': 1024,
                     'window_height': 768,
                     'max_recording_history': 20,
                     'y_distance_presets': [20., 30., 40., 50., 100., 200.],
                     'y_scale_presets': [.1, .2, .5, 1, 2, 5, 10],
                     'window_length_presets': [1., 5., 10., 20., 30., 60.],
                     'read_intervals': 10 * 60.,
                     'recording_dir': '/home/gio/recordings',
                     }
DEFAULTS['video'] = {'vlc_exe': 'C:/Program Files (x86)/VideoLAN/VLC/vlc.exe',
                     'vlc_width': 640,
                     'vlc_height': 480,
                     }


class Preferences(QDialog):

    def __init__(self, parent):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.parent = parent
        self.setWindowTitle('Preferences')

        self.create_preferences()

    def create_preferences(self):
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply
                                | QDialogButtonBox.Cancel)
        self.idx_ok = bbox.button(QDialogButtonBox.Ok)
        self.idx_apply = bbox.button(QDialogButtonBox.Apply)
        self.idx_cancel = bbox.button(QDialogButtonBox.Cancel)
        bbox.clicked.connect(self.button_clicked)

        page_list = QListWidget()
        page_list.setSpacing(1)
        page_list.currentRowChanged.connect(self.change_widget)

        pages = ['General', 'Overview', 'Signals', 'Spectrum', 'Notes', 'Detection', 'Video']
        for one_page in pages:
            page_list.addItem(one_page)

        self.stacked = QStackedWidget()
        self.stacked.addWidget(self.parent.config)
        self.stacked.addWidget(self.parent.overview.config)
        self.stacked.addWidget(self.parent.traces.config)
        self.stacked.addWidget(self.parent.spectrum.config)
        self.stacked.addWidget(self.parent.stages.config)
        self.stacked.addWidget(self.parent.detect.config)
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
        self.stacked.setCurrentIndex(new_row)

    def button_clicked(self, button):
        if button in (self.idx_ok, self.idx_apply):
            for i_config in range(self.stacked.count()):
                one_config = self.stacked.widget(i_config)
                if one_config.modified:
                    lg.debug('Preferences for ' + one_config.widget +
                             ' were modified')
                    one_config.get_values()
                    # TODO: try (if dataset is available)
                    one_config.update_widget()
                    one_config.modified = False

            if button == self.idx_ok:
                self.accept()

        if button == self.idx_cancel:
            self.reject()


class Config(QWidget):
    """You'll need to implement one methods:
        - create_config with the QGroupBox and layouts

    """
    def __init__(self, widget, update_widget):
        super().__init__()

        self.modified = False
        self.widget = widget
        value_names = list(DEFAULTS[widget].keys())

        self.value = self.create_values(value_names)
        self.index = self.create_indices(value_names)

        # I'm surprised this works, it calls the overloaded method already
        self.create_config()
        self.set_values()
        self.update_widget = update_widget

    def create_values(self, value_names):
        # it should read the preferences
        output = {}
        for value_name in value_names:
            output[value_name] = read_settings(self.widget, value_name)

        return output

    def create_indices(self, value_names):
        # default to None as long as we don't have an index
        return dict(zip(value_names, [None] * len(value_names)))

    def get_values(self):
        # GET VALUES FROM THE GUI
        for value_name, widget in self.index.items():
            self.value[value_name] = widget.get_value()  # TODO: pass defaults

            setting_name = self.widget + '/' + value_name
            settings.setValue(setting_name, self.value[value_name])

    def set_values(self):
        # SET VALUES TO THE GUI
        for value_name, widget in self.index.items():
            widget.set_value(self.value[value_name])
            widget.connect(self.set_modified)  # also connect to modified

    def create_config(self):
        # TO BE OVERLOAD
        pass

    def set_modified(self):
        self.modified = True


def read_settings(widget, value_name):

    setting_name = widget + '/' + value_name
    default_value = DEFAULTS[widget][value_name]

    default_type = type(default_value)
    if default_type is list:
        default_type = type(default_value[0])

    val = settings.value(setting_name, default_value, type=default_type)
    return val


class FormBool(QCheckBox):
    def __init__(self, checkbox_label):
        super().__init__(checkbox_label)

    def get_value(self, default=False):
        return self.checkState() == Qt.Checked

    def set_value(self, value):
        if value:
            self.setCheckState(Qt.Checked)
        else:
            self.setCheckState(Qt.Unchecked)

    def connect(self, funct):
        # TODO:
        pass


class FormFloat(QLineEdit):
    """Subclass QLineEdit for floats.
    value is read directly from defaults

    """
    def __init__(self):
        super().__init__('')

    def get_value(self, default=0):
        """Get float from widget.

        Parameters
        ----------
        default : float
            default value for the parameter

        Returns
        -------
        float
            the value in text or default

        """
        text = self.text()
        try:
            text = float(text)
        except ValueError:
            lg.debug('Cannot convert "' + str(text) + '" to float.' +
                     'Using default ' + str(default))
            text = default
            self.set_value(text)
        return text

    def set_value(self, value):
        self.setText(str(value))

    def connect(self, funct):
        self.textEdited.connect(funct)


class FormInt(QLineEdit):
    """Subclass QLineEdit for floats.
    value is read directly from defaults

    """
    def __init__(self):
        super().__init__('')

    def get_value(self, default=0):
        """Get float from widget.

        Parameters
        ----------
        default : float
            default value for the parameter

        Returns
        -------
        float
            the value in text or default

        """
        text = self.text()
        try:
            text = int(text)
        except ValueError:
            lg.debug('Cannot convert "' + str(text) + '" to int. ' +
                     'Using default ' + str(default))
            text = default
            self.set_value(text)
        return text

    def set_value(self, value):
        self.setText(str(value))

    def connect(self, funct):
        self.textEdited.connect(funct)


class FormStr(QLineEdit):
    """Subclass QLineEdit for strings.

    value is read directly from defaults
    """
    def __init__(self):
        super().__init__('')

    def get_value(self, default=''):
        """Get string from widget."""
        return self.text()

    def set_value(self, value):
        self.setText(value)

    def connect(self, funct):
        self.textEdited.connect(funct)


class FormList(QLineEdit):
    """Subclass QLineEdit for strings.

    value is read directly from defaults
    """
    def __init__(self):
        super().__init__('')

    def get_value(self, default=None):
        """Get string from widget."""
        if default is None:
            default = []

        try:
            text = literal_eval(self.text())
            if not isinstance(text, list):
                pass
                # raise ValueError

        except ValueError:
            lg.debug('Cannot convert "' + str(text) + '" to list. ' +
                     'Using default ' + str(default))
            text = default
            self.set_value(text)

        return text

    def set_value(self, value):
        self.setText(str(value))

    def connect(self, funct):
        self.textEdited.connect(funct)
