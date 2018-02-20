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


class SpindleHelp(HelpDialog):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        s = ('<h3>Spindle detection help</h3>'
             ''
             'Note: Epochs marked as bad signal are excluded from detection.'
             '<br /><br />'
             '<b>Label</b><br />'
             'Label for this event type, to appear on trace.<br /><br />'
             '<b>Channel group</b><br />'
             'Channel group containing desired channel(s).<br /><br />'
             '<b>Channel(s)</b><br />'
             'One or several channels on which to detect slow waves.<br />'
             '<br />'
             '<b>Stage(s)</b><br />'
             'One or several stages during which to detect slow waves. '
             'If none are selected, all stages will be scanned.<br /><br />'
             '<b>Merge events across channels</b>'
             'If selected, spindles detected on different channels and '
             'separated by less than <b>Minimum interval</b> will be merged '
             'into a single event, to the channel with the earliest onset '
             'spindle.<br />'
             ''
             '<h4>Spindle detection methods</h4>'
             '<p>'
             'The method options in the spindle detection dialog are direct '
             'implementations of spindle detection methods '
             'reported in the scholarly articles cited below. '
             'For customizable parameters (in bold), the values used in the '
             'article are specified in square brackets []. '
             'Further details on the original method are provided in italics. '
             '</p>'

             '<p>'
             '<b>Wamsley, E. J. et al. (2012) Biol. Psychiatry 71, 154-61</b>'
             '<ol>'
             '<i><li>Authors analyzed spindles during NREM2. EEG data were '
             'filtered at 0.5–35Hz.</li></i>'
             '<li>The artifact-free EEG signal is subjected to a time-'
             'frequency transformation using an 8-parameter complex Morlet '
             'wavelet with the average of <b>Lowcut</b> and <b>Highcut</b> as '
             'the frequency, with σ = <b>Wavelet sigma</b> [0.5] s and with '
             'window size = <b>Detection window</b> [1] s.</li>'
             '<li>The resulting complex-valued time series is squared.</li>'
             '<li>The imaginary part of the time-series is discarded, and the '
             'remaining real-valued time series is squared again.'
             '<li>The moving average of the real signal is calculated, '
             'using a sliding window of size = <b>Smoothing</b> [0.1] s.</li>'
             '<li>A spindle event is identified whenever this wavelet signal '
             'exceeds threshold, defined as <b>Detection threshold</b> [4.5] '
             'times the mean signal amplitude of all artifact-free '
             'epochs, between <b>Minimum duration</b> [0.4] s '
             'and <b>Maximum duration</b> s [no maximum]. In this '
             'implementation, threshold crossings define the spindle start and '
             'end times, but see next point for the original method.</li>'
             '<i><li>The duration of each spindle was calculated as the '
             'half-height width of wavelet energy within the spindle '
             'frequency range.</li></i>'
             '</ol>'
             '</p>'

             '<p>'
             '<b>Nir, Y. et al. (2011) Neuron 70, 153-69</b>'
             '<ol>'
             '<i><li>The channels with spindle activity in NREM sleep are '
             'chosen for further analysis (significant spectral power '
             'increases in spindle range as compared with a 1/f model, '
             'p &lsaquo; 0.001, paired t-test across 10 s segments.)</li></i>'
             '<li>The EEG signal is bandpass filtered between <b>Lowcut</b> '
             '[10] Hz and <b>Highcut</b> [16] Hz with a zero-phase 4th order '
             'Butterworth filter. </li>'
             '<li>Instantaneous amplitude in the sigma frequency is '
             'extracted via the Hilbert transform.</li>'
             '<li>To avoid excessive multiple crossings of thresholds within '
             'the same spindle event, instantaneous amplitude is temporally '
             'smoothed using a Gaussian kernel of σ = <b>Smoothing</b> [0.4] '
             's.'
             '</li>'
             '<li>Events with amplitude greater than mean + <b>Detection '
             'threshold</b> [3] SD (computed across all artifact-free <i>NREM '
             'sleep</i> epochs) are considered putative spindles and '
             'detections within <b>Minimum interval</b> [1] s are merged.</li>'
             '<li>A threshold of mean + <b>Selection threshold</b> [1] SD '
             'defines start and end times, and events with duration between '
             '<b>Minimum duration</b> [0.5] s and <b>Maximum duration</b> [2] '
             's are selected for further analysis.'
             '</i></li>'
             '<i><li>Those channels, in which an increase in spectral power '
             'within the detected events was restricted to the spindle-'
             'frequency range (10-16 Hz) rather than broadband (unpaired '
             't-test (α=0.001) between maximal spectral power in detected vs. '
             'random events), and with at least 1 spindle per min of NREM '
             'sleep were chosen for further analysis. Authors focused on the '
             'frontal and parietal channels, where spindle-events could be '
             'reliably detected and successfully separated from paroxysmal '
             'events. This highly conservative procedure of including in the '
             'analysis only the channels with high spindle SNR, ensured that '
             'local occurrence of spindle events does not arise merely as a '
             'result of the lack of spindles or poor spindle SNR in some '
             'channels.</li></i>'
             '</ol>'
             '</p>'

             '<p>'
             '<b>Mölle, M. et al. (2011) Sleep 34, 1411-21</b>'
             '<ol>'
             '<li>The <i>NREM</i> signal is bandpass filtered between '
             '<b>Lowcut</b> and <b>Highcut</b>, using a zero-phase 4th order '
             'Butterworth filter. '
             '<i>Authors used the adapted sigma peak +/- 1.5 Hz.</i></li>'
             '<li>The root-mean-square of the signal is taken, with a '
             'moving window of size = <b>Detection window</b> [0.2] s.</li>'
             '<li>The resulting RMS signal is smoothed with a moving '
             'average of window size = <b>Smoothing</b> [0.2] s.</li>'
             '<li>Spindles are detected as a continuous rise in the '
             'smoothed RMS signal above <b>Detection threshold</b> [1.5] SDs, '
             'lasting between <b>Minimum duration</b> [0.5] s and <b>Maximum '
             'duration</b> [3] s. Spindle start and end times are the '
             'threshold crossings.</li>'
             '</ol>'
             '</p>'

             '<p>'
             '<b>Ferrarelli, F. et al. (2007) Am. J. Psychiatry 164, 483-92'
             '</b>'
             '<ol>'
             '<li>The <i>NREM</i> signal is bandpass filtered between '
             '<b>Lowcut</b> [12] Hz and <b>Highcut</b> [15] Hz. Authors did '
             'not specify a filter; this software employs a zero-phase 4th '
             'order Butterworth filter.</li>'
             '<li>The filtered signal is rectified.</li>'
             '<li>Upper and lower thresholds are set at <b>Detection '
             'threshold</b> [8] and <b>Selection threshold</b> [2] times the '
             'average amplitude of the time series.</li>'
             '<li>Spindles are detected when the time series amplitude '
             'exceeds the upper threshold. This is the spindle peak.</li>'
             '<li>Spindle start and end times are set at the time points '
             'immediately preceding and following this peak when the '
             'amplitude of the time series drops below the lower threshold.'
             '</li>'
             '<li>The authors did not set minimum or maximum durations.</li>'
             '</ol>'
             '</p>'

             '<p>'
             '<b>UCSD</b>'
             '<ol>'
             '<li>The raw EEG signal is subjected to a time-frequency '
             'transformation using real wavelets with frequencies from '
             '<b>Lowcut</b> to <b>Highcut</b> at 0.5-Hz intervals, with width '
             '= 0.5 s and with window size = <b>Detection window</b> [1] s.'
             '</li>'
             '<li>The resulting time-frequency signals are rectified and '
             'convolved with a Tukey window of size = 0.5 s, then '
             'averaged to produce a single time-frequency signal.</li>'
             '<li>A threshold is defined as the signal median plus '
             '<b>Detection threshold</b> [2] SDs.</li>'
             '<li>Spindles are detected at each relative maximum in the '
             'signal which exceeds the threshold.</li>'
             '<li>Steps 1-3 are repeated on the raw signal, this time with '
             'width = 0.2 s, with Tukey window size = 0.2 s, and with the '
             'threshold set at <b>Selection threshold</b> [1] SD.</li>'
             '<li>Spindle start and end times are defined at threshold '
             'crossings.</li>'
             '<li>Spindles are retained if their duration is between '
             '<b>Minimum duration</b> and <b>Maximum duration</b>.</li>'
             ''
             '</ol></p>'
             )
        self.resize(500, 700)
        self.set_text(s)


class SlowWaveHelp(HelpDialog):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        s = ('<h3>Slow wave detection help</h3>'
             ''
             'Note: Epochs marked as bad signal are excluded from detection.'
             '<br /><br />'
             '<b>Label</b><br />'
             'Label for this event type, to appear on trace.<br /><br />'
             '<b>Channel group</b><br />'
             'Channel group containing desired channel(s).<br /><br />'
             '<b>Channel(s)</b><br />'
             'One or several channels on which to detect slow waves.<br />'
             '<br />'
             '<b>Stage(s)</b><br />'
             'One or several stages during which to detect slow waves. '
             'If none are selected, all stages will be scanned.<br /><br />'
             '<b>Invert detection</b><br />'
             'If selected, the algorithm will detect inverted slow waves, '
             'i.e. positive-then-negative instead of negative-then-positive. '
             '<br />'
             ''
             '<h4>Slow wave detection methods</h4>'
             '<p>'
             'The method options in the slow wave detection dialog are direct '
             'implementations of slow wave detection methods '
             'reported in the scholarly articles cited below. '
             'For customizable parameters (in bold), the values used in the '
             'article are specified in square brackets []. '
             'Further details on the original method are provided in italics. '
             '</p>'

             '<p>'
             '<b>Massimini, M. et al. (2004) J Neurosci 24(31), 6862-70</b>'
             '<ol>'
             '<i><li>256-channel EEG is re-referenced to the average of the '
             'signals from the earlobes.</li></i>'
             '<i><li>EEG signal is locally averaged over 4 non-overlapping '
             'regions of the scalp.</li></i>'
             '<li>The <i>NREM</i> signal is bandpass filtered between '
             '<b>Lowcut</b> and <b>Highcut</b>, using a zero-phase 4th order '
             'Butterworth filter. '
             '<li>Slow waves are detected when the following 3 criteria are '
             'met:'
             '<ol>'
             '<li>A negative zero crossing and a subsequent positive zero '
             'crossing separated by <b>Minimum trough duration</b> [0.3] '
             'and <b>Maximum trough duration</b> [1.0] s.</li>'
             '<li>A negative peak between the two zero crossings with voltage '
             'less than <b>Maximum trough amplitude</b> [-80] &mu;V'
             '<li>A negative-to-positive peak-to-peak amplitude greater than '
             '<b>Minimum peak-to-peak amplitude</b> [140] &mu;V.'
             '</ol></ol>'
             '</p>'
             ''
             '<p>'
             '<b>AASM/Massimini2004</b><br /><br />'
             'This is a reimplementation of Massimini et al., 2004 (above), '
             'except with default values for slow waves as defined by the '
             'American Academy of Sleep Medicine (AASM).'
             )
        self.resize(500, 700)
        self.set_text(s)


class EvtAnalysisHelp(HelpDialog):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        s = ('<h2>Event analysis</h2>'
             ''
             '<h3>Bandpass</h3>'
             '<h4>Lowcut and Highcut</h4>'
             'Lower and upper band limits for analysis. For <b>Maximum '
             'amplitude</b>, <b>Peak-to-peak amplitude</b> and <b>RMS</b>, '
             'limits are used to bandpass filter the signal, using a 4th-'
             'order zero-phase Butterworth filter. '
             'For <b>Peak frequency</b> and <b>Average power</b>, limits set '
             'the minimum and maximum frequencies of interest.'
             '<br />'
             ''
             '<h3>Parameters, global</h3>'
             '<h4>Count</h4>'
             'Total number of events detected in the queried stage(s).'
             '<h4>Density</h4>'
             'Number of events per epoch of the queried stage(s). '
             'Epoch duration can be set in Preferences &rarr; Notes &rarr; '
             'Length of scoring window. Change will not take effect until a '
             'new rater is created.'
             '<br />'
             ''
             '<h3>Parameters, per event</h3>'
             '<h4>Duration</h4>'
             'Duration of the event in seconds. Event start and end are as '
             'seen on the trace.'
             '<h4>Maximum amplitude</h4>'
             'Maximum value of the event signal, in &mu;V, after bandpass '
             'filtering. If raw signal is inverted, this will give the signal '
             'minimum (most negative value).'
             '<h4>Peak-to-peak amplitude</h4>'
             'Absolute difference between the event signal maximum and '
             'minimum, in &mu;V, after bandpass filtering.'
             '<h4>Peak frequency</h4>'
             'Frequency, in Hz, associated with the highest power spectral '
             'density within the specified band, after removal of 1/f noise '
             '(signal whitening). Power spectral density is estimated with a '
             'simple periodogram.'
             '<h4>Average power</h4>'
             'Average value of the power spectral density within the '
             'specified band, in &mu;V&sup2;, after  removal of 1/f noise '
             '(signal whitening). Power spectral density is estimated with a '
             'simple periodogram.'
             '<h4>RMS</h4>'
             'Square root of the mean of the square of all event signal '
             'values, in &mu;V, after (1) bandpass filtering and (2) removal '
             'of 1/f noise (signal whitening). '
             '<br />'
             ''
             '<h3>Options</h3>'
             '<h4>Log transform</h4>'
             'If checked, all parameters (global and per event) will be '
             'reported as their natural logarithms. This allows the use of '
             'general linear model staistics on log-normally distributed '
             'data. '
             'For more information, see <i>Buzsáki G, Mizuseki K. The '
             'log-dynamic brain: how skewed distributions affect network '
             'operations. Nature reviews. Neuroscience. 2014 Apr;15(4):264.'
             '</i>'
             '<h4>Frequency split</h4>'
             'If checked, events will be analyzed separately based on whether '
             'their peak frequency is above or below the specified frequency. '
             'Global parameters and averages will be calculated separately '
             'for both groups, and output will be saved in separate CSV '
             'files.'
             '<h4>Cycle split</h4>'
             'If checked, events will be analyzed separately by sleep cycle. '
             'Global parameters and averages will be calculated separately '
             'for each group, and output will be saved in separate CSV files.'
             )
        self.resize(500, 700)
        self.set_text(s)
