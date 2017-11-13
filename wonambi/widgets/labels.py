"""Widget to redefine the labels.
"""
from logging import getLogger
from pathlib import Path
from re import split

from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QColor,
                         )

from PyQt5.QtWidgets import (QAbstractItemView,
                             QFileDialog,
                             QHBoxLayout,
                             QPushButton,
                             QVBoxLayout,
                             QTableWidget,
                             QTableWidgetItem,
                             QWidget
                             )

lg = getLogger(__name__)


class Labels(QWidget):
    """
    Attributes
    ----------
    chan_name : list of str
        list of all the labels (with the user-defined changes)
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.filename = None
        self.chan_name = None  # None when dataset is not loaded

        self.create()

    def create(self):

        self.idx_load = QPushButton('Load')
        self.idx_load.clicked.connect(self.load_labels)
        self.idx_load.setToolTip('Load file with a list of channels (separated by , or ; or tabs or spaces).')
        self.idx_save = QPushButton('Save')
        self.idx_save.clicked.connect(self.save_labels)
        self.idx_save.setEnabled(False)

        # cancel is equal to setting labels to what they were
        self.idx_cancel = QPushButton('Cancel')
        self.idx_cancel.clicked.connect(self.update)
        self.idx_apply = QPushButton('Apply')
        self.idx_apply.clicked.connect(self.apply)
        self.idx_apply.setToolTip('Changes will take effect. This will reset the channel groups and traces.')

        layout_0 = QHBoxLayout()
        layout_0.addWidget(self.idx_load)
        layout_0.addWidget(self.idx_save)

        layout_1 = QHBoxLayout()
        layout_1.addWidget(self.idx_cancel)
        layout_1.addWidget(self.idx_apply)

        self.table = QTableWidget()

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Current Labels', 'New Labels'])

        self.table.cellChanged.connect(self.check_labels)

        layout = QVBoxLayout()
        layout.addLayout(layout_0)
        layout.addWidget(self.table)
        layout.addLayout(layout_1)

        self.setLayout(layout)

        self.setEnabled(False)

    def update(self, checked=False, labels=None, custom_labels=None):
        """Use this function when we make changes to the list of labels or when
        we load a new dataset.

        Parameters
        ----------
        checked : bool
            argument from clicked.connect
        labels : list of str
            list of labels in the dataset (default)
        custom_labels : list of str
            list of labels from a file
        """
        if labels is not None:
            self.setEnabled(True)
            self.chan_name = labels

        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setRowCount(len(self.chan_name))

        for i, label in enumerate(self.chan_name):
            old_label = QTableWidgetItem(label)
            old_label.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            if custom_labels is not None and i < len(custom_labels) and custom_labels[i]:  # it's not empty string or None
                label_txt = custom_labels[i]
            else:
                label_txt = label
            new_label = QTableWidgetItem(label_txt)

            self.table.setItem(i, 0, old_label)
            self.table.setItem(i, 1, new_label)

        self.table.blockSignals(False)

    def check_labels(self):

        # read new labels first
        labels = self._read_labels()

        # disable apply, if there are duplicates
        if len(labels) == len(set(labels)):
            self.idx_apply.setEnabled(True)
        else:
            self.idx_apply.setEnabled(False)

        # mark duplicates in red
        self.table.blockSignals(True)
        for i, label in enumerate(labels):
            if labels.count(label) > 1:
                self.table.item(i, 1).setBackground(QColor('red'))
            else:
                self.table.item(i, 1).setBackground(QColor('white'))
        self.table.blockSignals(False)

    def load_labels(self, checked=False, test_name=None):
        if self.filename is not None:
            filename = self.filename
        elif self.parent.info.filename is not None:
            filename = Path(self.parent.info.filename)
        else:
            filename = None

        if test_name:
            filename = test_name
        else:
            filename, _ = QFileDialog.getOpenFileName(self,
                                                      'Open Labels',
                                                      str(filename.parent),
                                                      'Comma-separated values (*.csv);; Text file (*.txt);; All Files(*.*)')
        if filename == '':
            return

        self.filename = Path(filename)

        with self.filename.open() as f:
            text = f.read()

        labels = split(', |,|; |;|\t|\n| ', text)
        labels = [label.strip() for label in labels]
        self.update(custom_labels=labels)

    def save_labels(self):
        """Save labels modified by the user.

        TODO
        ----
        Save labels modified by the user
        """
        pass

    def apply(self):

        self.chan_name = self._read_labels()
        self.parent.info.dataset.header['chan_name'] = self.chan_name

        self.parent.channels.reset()
        self.parent.channels.update()
        self.parent.traces.reset()

    def reset(self):
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.blockSignals(False)

        self.setEnabled(False)

    def _read_labels(self):

        labels = []
        for i in range(self.table.rowCount()):
            labels.append(self.table.item(i, 1).text())

        return labels
