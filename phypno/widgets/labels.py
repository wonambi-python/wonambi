"""Widget to redefine the labels.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QColor,
                         )

from PyQt5.QtWidgets import (QAbstractItemView,
                             QHBoxLayout,
                             QPushButton,
                             QVBoxLayout,
                             QTableWidget,
                             QTableWidgetItem,
                             QWidget
                             )


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
        self.chan_name = []

        self.create()

    def create(self):

        self.idx_load = QPushButton('Load')
        self.idx_load.clicked.connect(self.load_labels)
        self.idx_save = QPushButton('Save')
        self.idx_save.clicked.connect(self.save_labels)
        # cancel is equal to setting labels to what they were
        self.idx_cancel = QPushButton('Cancel')
        self.idx_cancel.clicked.connect(self.update)
        self.idx_apply = QPushButton('Apply')
        self.idx_apply.clicked.connect(self.apply)

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

    def update(self, labels):
        """Use this function when we make changes to the list of labels or when
        we load a new dataset.

        Parameters
        ----------
        labels : list of str
            labels
        """
        self.chan_name = labels

        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setRowCount(len(labels))

        for i, label in enumerate(labels):
            old_label = QTableWidgetItem(label)
            old_label.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            new_label = QTableWidgetItem(label)
            self.table.setItem(i, 0, old_label)
            self.table.setItem(i, 1, new_label)
        self.table.blockSignals(False)

    def check_labels(self):

        # read new labels first
        labels = []
        for i in range(self.table.rowCount()):
            labels.append(self.table.item(i, 1).text())

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

    def load_labels(self):
        pass

    def save_labels(self):
        pass

    def apply(self):

        labels = []
        for i in range(self.table.rowCount()):
            labels.append(self.table.item(i, 1).text())

        self.chan_name = labels

        # refresh other widgets (channels, traces)

    def reset(self):
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.blockSignals(False)

