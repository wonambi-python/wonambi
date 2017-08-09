# -*- coding: utf-8 -*-
"""
A short Python script
=====================

A script that is not executed when gallery is generated but nevertheless
gets included as an example.
Doing a list
"""

# test gio

print([i for i in range(10)])

# second test
from PyQt5.QtCore import QTimer
from phypno.scroll_data import MainWindow

print('one line before')
print('during')
w = MainWindow()
print('during 2')

w.grab().save('test.png')
QTimer.singleShot(100, w.close)


print('one line after')
