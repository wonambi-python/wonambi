#!/usr/bin/env python3

from PyQt5.QtWidgets import QApplication
app = QApplication([])

with open('plot_code.py') as f:
    exec(f.read())

with open('plot_code1.py') as f:
    exec(f.read())

app.exec_()
