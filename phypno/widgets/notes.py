from logging import getLogger
lg = getLogger(__name__)

from PySide.QtGui import (QComboBox,
                          QFormLayout,
                          QPushButton,
                          QLabel,
                          QListWidget,
                          QTableView,
                          QWidget,
                          )


class Bookmarks(QListWidget):
    """

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent

    def update_overview(self):
        """

        """
        self.display_overview()

    def display_overview(self):
        pass



class Events(QWidget):
    """

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.combobox = QComboBox()
        self.table = QTableView()

        layout = QFormLayout()
        layout.addRow('Events: ', self.combobox)
        layout.addRow('List: ', self.table)
        self.setLayout(layout)

    def update_overview(self):
        """

        """
        self.display_overview()

    def display_overview(self):
        pass


class Stages(QWidget):
    """

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.filename = QPushButton()
        self.rater = QLabel()
        self.combobox = QComboBox()

        layout = QFormLayout()
        layout.addRow('Filename: ', self.filename)
        layout.addRow('Rater: ', self.rater)
        layout.addRow('Stage: ', self.combobox)
        self.setLayout(layout)

    def update_overview(self):
        """

        """
        self.display_overview()

    def display_overview(self):
        pass
