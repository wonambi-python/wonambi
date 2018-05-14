"""Various functions used for the GUI.
"""
from ast import literal_eval
from logging import getLogger
from math import ceil, floor
from numpy import arange
from os.path import dirname, join, realpath

from PyQt5.QtCore import QRectF, QSettings, Qt
from PyQt5.QtGui import (QBrush,
                         QColor,
                         QPainterPath,
                         QPainter,
                         )
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import (QCheckBox,
                             QComboBox,
                             QCommonStyle,
                             QFileDialog,
                             QGraphicsItem,
                             QGraphicsRectItem,
                             QGraphicsSimpleTextItem,
                             QLineEdit,
                             QMessageBox,
                             QPushButton,
                             QRadioButton,
                             QSpinBox,
                             )


lg = getLogger(__name__)

LINE_WIDTH = 0  # COSMETIC LINE
LINE_COLOR = 'black'
# TODO: this in ConfigNotes
STAGE_NAME = ['NREM1', 'NREM2', 'NREM3', 'REM', 'Wake', 'Movement',
              'Undefined', 'Unknown', 'Artefact']

MAX_LENGTH = 20

stdicon = QCommonStyle.standardIcon


icon_path = join(dirname(realpath(__file__)), 'icons')
oxy_path = join(icon_path, 'oxygen')

ICON = {'application': join(icon_path, 'wonambi.jpg'),
        'open_rec': join(oxy_path, 'document-open.png'),
        'page_prev': join(oxy_path, 'go-previous-view.png'),
        'page_next': join(oxy_path, 'go-next-view.png'),
        'step_prev': join(oxy_path, 'go-previous.png'),
        'step_next': join(oxy_path, 'go-next.png'),
        'chronometer': join(oxy_path, 'chronometer.png'),
        'up': join(oxy_path, 'go-up.png'),
        'down': join(oxy_path, 'go-down.png'),
        'zoomin': join(oxy_path, 'zoom-in.png'),
        'zoomout': join(oxy_path, 'zoom-out.png'),
        'zoomnext': join(oxy_path, 'zoom-next.png'),
        'zoomprev': join(oxy_path, 'zoom-previous.png'),
        'ydist_more': join(oxy_path, 'format-line-spacing-triple.png'),
        'ydist_less': join(oxy_path, 'format-line-spacing-normal.png'),
        'selchan': join(oxy_path, 'mail-mark-task.png'),
        'widget': join(oxy_path, 'window-duplicate.png'),
        'settings': join(oxy_path, 'configure.png'),
        'quit': join(oxy_path, 'window-close.png'),
        'bookmark': join(oxy_path, 'bookmarks-organize.png'),
        'event': join(oxy_path, 'edit-table-cell-merge.png'),
        'new_eventtype': join(oxy_path, 'edit-table-insert-column-right.png'),
        'del_eventtype': join(oxy_path, 'edit-table-delete-column.png'),
        'help-about': join(oxy_path, 'help-about.png')
        }

settings = QSettings("wonambi", "wonambi")


class Path(QPainterPath):
    """Paint a line in the simplest possible way.

    Parameters
    ----------
    x : ndarray or list
        x-coordinates
    y : ndarray or list
        y-coordinates
    """
    def __init__(self, x, y):
        super().__init__()

        self.moveTo(x[0], y[0])
        for i_x, i_y in zip(x, y):
            self.lineTo(i_x, i_y)


class RectMarker(QGraphicsRectItem):
    """Class to draw a rectangular, coloured item.

    Parameters
    ----------
    x : float
        x position in scene
    y : gloat
        y position in scene
    width : float
        length in seconds
    height : float
        height in scene units
    color : str or QColor, optional
        color of the rectangle
    """
    def __init__(self, x, y, width, height, zvalue, color='blue'):
        super().__init__()

        self.color = color
        self.setZValue(zvalue)
        buffer = 1
        self.marker = QRectF(x, y, width, height)
        self.b_rect = QRectF(x - buffer / 2, y + buffer / 2, width + buffer,
                             height + buffer)

    def boundingRect(self):
        return self.b_rect

    def paint(self, painter, option, widget):
        color = QColor(self.color)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.marker)
        super().paint(painter, option, widget)

    def contains(self, pos):
        return self.marker.contains(pos)


class TextItem_with_BG(QGraphicsSimpleTextItem):
    """Class to draw text with dark background (easier to read).

    Parameters
    ----------
    bg_color : str or QColor, optional
        color to use as background
    """
    def __init__(self, bg_color='black'):
        super().__init__()

        self.bg_color = bg_color
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setBrush(QBrush(Qt.white))

    def paint(self, painter, option, widget):
        bg_color = QColor(self.bg_color)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.boundingRect())
        super().paint(painter, option, widget)

class FormBool(QCheckBox):
    """Subclass QCheckBox to have a more consistent API across widgets.

    Parameters
    ----------
    checkbox_label : str
        label next to checkbox

    """
    def __init__(self, checkbox_label):
        super().__init__(checkbox_label)

    def get_value(self, default=False):
        """Get the value of the QCheckBox, as boolean.

        Parameters
        ----------
        default : bool
            not used

        Returns
        -------
        bool
            state of the checkbox

        """
        return self.checkState() == Qt.Checked

    def set_value(self, value):
        """Set value of the checkbox.

        Parameters
        ----------
        value : bool
            value for the checkbox

        """
        if value:
            self.setCheckState(Qt.Checked)
        else:
            self.setCheckState(Qt.Unchecked)

    def connect(self, funct):
        """Call funct when user ticks the box.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.stateChanged.connect(funct)


class FormRadio(QRadioButton):
    """Subclass QRadioButton to have a more consistent API across widgets.

    Parameters
    ----------
    checkbox_label : str
        label next to checkbox

    """
    def __init__(self, checkbox_label):
        super().__init__(checkbox_label)

    def get_value(self, default=False):
        """Get the value of the QCheckBox, as boolean.

        Parameters
        ----------
        default : bool
            not used

        Returns
        -------
        bool
            state of the checkbox

        """
        return self.isChecked == Qt.Checked

    def set_value(self, value):
        """Set value of the checkbox.

        Parameters
        ----------
        value : bool
            value for the checkbox

        """
        if value:
            self.setChecked(Qt.Checked)
        else:
            self.setChecked(Qt.Unchecked)

    def connect(self, funct):
        """Call funct when user ticks the box.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.toggled.connect(funct)


class FormFloat(QLineEdit):
    """Subclass QLineEdit for float to have a more consistent API across
    widgets.

    """
    def __init__(self, default=None):
        super().__init__('')

        if default is not None:
            self.set_value(default)

    def get_value(self, default=0):
        """Get float from widget.

        Parameters
        ----------
        default : float
            default value for the parameter in case it fails

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
        """Set value of the float.

        Parameters
        ----------
        value : float
            value for the line edit

        """
        self.setText(str(value))

    def connect(self, funct):
        """Call funct when the text was changed.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.textEdited.connect(funct)


class FormInt(QLineEdit):
    """Subclass QLineEdit for int to have a more consistent API across widgets.

    """
    def __init__(self, default=None):
        super().__init__('')

        if default is not None:
            self.set_value(default)

    def get_value(self, default=0):
        """Get int from widget.

        Parameters
        ----------
        default : int
            default value for the parameter in case it fails

        Returns
        -------
        int
            the value in text or default

        """
        text = self.text()
        try:
            text = int(float(text))  # to convert values like 30.0
        except ValueError:
            lg.debug('Cannot convert "' + str(text) + '" to int. ' +
                     'Using default ' + str(default))
            text = default
            self.set_value(text)
        return text

    def set_value(self, value):
        """Set value of the int.

        Parameters
        ----------
        value : int
            value for the line edit

        """
        self.setText(str(value))

    def connect(self, funct):
        """Call funct when the text was changed.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.textEdited.connect(funct)


class FormList(QLineEdit):
    """Subclass QLineEdit for lists to have a more consistent API across
    widgets.

    """
    def __init__(self):
        super().__init__('')

    def get_value(self, default=None):
        """Get int from widget.

        Parameters
        ----------
        default : list
            list with widgets

        Returns
        -------
        list
            list that might contain int or str or float etc

        """
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
        """Set value of the list.

        Parameters
        ----------
        value : list
            value for the line edit

        """
        self.setText(str(value))

    def connect(self, funct):
        """Call funct when the text was changed.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.textEdited.connect(funct)


class FormStr(QLineEdit):
    """Subclass QLineEdit for str to have a more consistent API across widgets.

    """
    def __init__(self):
        super().__init__('')

    def get_value(self, default=''):
        """Get int from widget.

        Parameters
        ----------
        default : str
            not used

        Returns
        -------
        str
            the value in text

        """
        return self.text()

    def set_value(self, value):
        """Set value of the string.

        Parameters
        ----------
        value : str
            value for the line edit

        """
        self.setText(value)

    def connect(self, funct):
        """Call funct when the text was changed.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.textEdited.connect(funct)


class FormDir(QPushButton):
    """Subclass QPushButton for str to have a more consistent API across widgets.

    Notes
    -----
    It calls to open the directory three times, but I don't understand why

    """
    def __init__(self):
        super().__init__('')

    def get_value(self, default=''):
        """Get int from widget.

        Parameters
        ----------
        default : str
            not used

        Returns
        -------
        str
            the value in text

        """
        return self.text()

    def set_value(self, value):
        """Set value of the string.

        Parameters
        ----------
        value : str
            value for the line edit

        """
        self.setText(value)

    def connect(self, funct):
        """Call funct when the text was changed.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        Notes
        -----
        There is something wrong here. When you run this function, it calls
        for opening a directory three or four times. This is obviously wrong
        but I don't understand why this happens three times. Traceback did not
        help.

        """
        def get_directory():
            rec = QFileDialog.getExistingDirectory(self,
                                                   'Path to Recording'
                                                   ' Directory')
            if rec == '':
                return

            self.setText(rec)
            funct()

        self.clicked.connect(get_directory)

class FormMenu(QComboBox):
    """Subclass QComboBox for dropdown menus to have a more consistent API
    across widgets.

    Parameters
    ----------
    input_list: list of str
        items to include in the dropdown menu / combobox
    """
    def __init__(self, input_list):
        super().__init__()

        if input_list is not None:
            for i in input_list:
                self.addItem(i)

    def get_value(self, default=None):
        """Get selection from widget.

        Parameters
        ----------
        default : str
            str for use by widget

        Returns
        -------
        str
            selected item from the combobox

        """
        if default is None:
            default = ''

        try:
            text = self.currentText()

        except ValueError:
            lg.debug('Cannot convert "' + str(text) + '" to list. ' +
                     'Using default ' + str(default))
            text = default
            self.set_value(text)

        return text

    def set_value(self, value):
        """Set value of the list.

        Parameters
        ----------
        value : str
            value for the combobox

        """
        self.setCurrentText(str(value))

    def connect(self, funct):
        """Call funct when the selection was changed.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.currentIndexChanged.connect(funct)

class FormSpin(QSpinBox):
    """Subclass QSpinBox for int to have a more consistent API across widgets.

    """
    def __init__(self, default=None, min_val=None, max_val=None, step=None):
        super().__init__()

        if default is not None:
            self.set_value(default)

        if min_val is not None:
            self.setMinimum(min_val)

        if max_val is not None:
            self.setMaximum(max_val)

        if step is not None:
            self.setSingleStep(step)

    def get_value(self, default=0):
        """Get int from widget.

        Parameters
        ----------
        default : int
            default value for the parameter in case it fails

        Returns
        -------
        int
            the value in text or default

        """
        text = self.value()
        try:
            text = int(float(text))
        except ValueError:
            lg.debug('Cannot convert "' + str(text) + '" to int. ' +
                     'Using default ' + str(default))
            text = default
            self.set_value(text)
        return text

    def set_value(self, value):
        """Set value of the int.

        Parameters
        ----------
        value : int
            value for the line edit

        """
        self.setValue(int(value))

    def connect(self, funct):
        """Call funct when the text was changed.

        Parameters
        ----------
        funct : function
            function that broadcasts a change.

        """
        self.valueChanged.connect(funct)

def keep_recent_datasets(max_dataset_history, info=None):
    """Keep track of the most recent recordings.

    Parameters
    ----------
    max_dataset_history : int
        maximum number of datasets to remember
    info : str, optional TODO
        path to file

    Returns
    -------
    list of str
        paths to most recent datasets (only if you don't specify
        new_dataset)
    """
    history = settings.value('recent_recordings', [])
    if isinstance(history, str):
        history = [history]

    if info is not None and info.filename is not None:
        new_dataset = info.filename

        if new_dataset in history:
            lg.debug(new_dataset + ' already present, will be replaced')
            history.remove(new_dataset)
        if len(history) > max_dataset_history:
            lg.debug('Removing last dataset ' + history[-1])
            history.pop()

        lg.debug('Adding ' + new_dataset + ' to list of recent datasets')
        history.insert(0, new_dataset)
        settings.setValue('recent_recordings', history)
        return None

    else:
        return history


def choose_file_or_dir():
    """Create a simple message box to see if the user wants to open dir or file

    Returns
    -------
    str
        'dir' or 'file' or 'abort'

    """
    question = QMessageBox(QMessageBox.Information, 'Open Dataset',
                           'Do you want to open a file or a directory?')
    dir_button = question.addButton('Directory', QMessageBox.YesRole)
    file_button = question.addButton('File', QMessageBox.NoRole)
    question.addButton(QMessageBox.Cancel)
    question.exec_()
    response = question.clickedButton()

    if response == dir_button:
        return 'dir'
    elif response == file_button:
        return 'file'
    else:
        return 'abort'


def short_strings(s, max_length=MAX_LENGTH):
    if len(s) > max_length:
        max_length -= 3  # dots
        start = ceil(max_length / 2)
        end = -floor(max_length / 2)
        s = s[:start] + '...' + s[end:]
    return s


def convert_name_to_color(s):
    """Convert any string to an RGB color.

    Parameters
    ----------
    s : str
        string to convert
    selection : bool, optional
        if an event is being selected, it's lighter

    Returns
    -------
    instance of QColor
        one of the possible color

    Notes
    -----
    It takes any string and converts it to RGB color. The same string always
    returns the same color. The numbers are a bit arbitrary but not completely.
    h is the baseline color (keep it high to have brighter colors). Make sure
    that the max module + h is less than 256 (RGB limit).

    The number you multiply ord for is necessary to differentiate the letters
    (otherwise 'r' and 's' are too close to each other).
    """
    h = 100
    v = [5 * ord(x) for x in s]
    sum_mod = lambda x: sum(x) % 100
    color = QColor(sum_mod(v[::3]) + h, sum_mod(v[1::3]) + h,
                   sum_mod(v[2::3]) + h)
    return color


def freq_from_str(freq_str):
    """Obtain frequency ranges from input string, either as list or dynamic
    notation.

    Parameters
    ----------
    freq_str : str
        String with frequency ranges, either as a list:
        e.g. [[1-3], [3-5], [5-8]];
        or with a dynamic definition: (start, stop, width, step).

    Returns
    -------
    list of tuple of float or None
        Every tuple of float represents a frequency band. If input is invalid,
        returns None.
    """
    freq = []
    as_list = freq_str[1:-1].replace(' ', '').split(',')

    try:
        if freq_str[0] == '[' and freq_str[-1] == ']':
            for i in as_list:
                one_band = i[1:-1].split('-')
                one_band = float(one_band[0]), float(one_band[1])
                freq.append(one_band)
    
        elif freq_str[0] == '(' and freq_str[-1] == ')':
    
            if len(as_list) == 4:
                start = float(as_list[0])
                stop = float(as_list[1])
                halfwidth = float(as_list[2]) / 2
                step = float(as_list[3])
                centres = arange(start, stop, step)
                for i in centres:
                    freq.append((i - halfwidth, i + halfwidth))
            else:
                return None
    
        else:
            return None           
    except:
        return None

    return freq


def export_graphics(MAIN, checked=False, test=None):

    from .modal_widgets import SVGDialog  # avoid circolar import

    if MAIN.info.filename is not None:
        filename = join(dirname(MAIN.info.filename), '*.svg')
    else:
        filename = None

    svg_dialog = SVGDialog(filename)

    if test is None:
        if not svg_dialog.exec():
            return
    else:
        svg_dialog.idx_file.setText(test)

    if svg_dialog.idx_list.currentText() == 'Traces':
        widget = MAIN.traces
    elif svg_dialog.idx_list.currentText() == 'Overview':
        widget = MAIN.overview

    svg_file = svg_dialog.idx_file.text()
    if not svg_file.endswith('.svg'):
        svg_file += '.svg'
    export_graphics_to_svg(widget, svg_file)


def export_graphics_to_svg(widget, filename):
    """Export graphics to svg

    Parameters
    ----------
    widget : instance of QGraphicsView
        traces or overview
    filename : str
        path to save svg
    """
    generator = QSvgGenerator()
    generator.setFileName(filename)
    generator.setSize(widget.size())
    generator.setViewBox(widget.rect())

    painter = QPainter()
    painter.begin(generator)
    widget.render(painter)
    painter.end()
