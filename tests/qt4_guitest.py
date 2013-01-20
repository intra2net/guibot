#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch
#
# guibender is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibender is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibender.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
from PyQt4 import QtGui, QtCore

app = QtGui.QApplication(sys.argv)

class ControlsWithLayout(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setWindowTitle('guibender test application')

        button_click = QtGui.QPushButton("Close on click()")
        self.connect(button_click, QtCore.SIGNAL('clicked()'),
            QtGui.qApp, QtCore.SLOT('quit()'))

        list_view = QtGui.QListWidget()
        list_view.addItem('Double click')
        self.connect(list_view, QtCore.SIGNAL("itemDoubleClicked (QListWidgetItem *)"), QtGui.qApp.quit)

        right_click_view = QtGui.QListWidget()
        right_click_view.addItem('Contextmenu')

        right_click_view.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu);

        quit_action = QtGui.QAction("Quit", self)
        right_click_view.addAction(quit_action)
        quit_action.triggered.connect(QtGui.qApp.quit)

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(button_click)
        hbox.addWidget(list_view)
        hbox.addWidget(right_click_view)

        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        self.resize(300, 100)

        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('cleanlooks'))

some_controls = ControlsWithLayout()
some_controls.show()

sys.exit(app.exec_())
