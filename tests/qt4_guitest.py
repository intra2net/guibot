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

        font_family = 'Helvetica'
        font_size = 10

        button_click = QtGui.QPushButton("Close on click()")
        button_click.setFixedSize(100, 20)
        button_click.setStyleSheet('QPushButton { font-family: ' + font_family + '; font-size: ' + str(font_size) + 't; }')
        self.connect(button_click, QtCore.SIGNAL('clicked()'), QtGui.qApp.quit)

        text_type = QtGui.QLineEdit()
        text_type.setPlaceholderText('type "quit"')
        text_type.setFixedSize(100, 20)
        self.connect(text_type, QtCore.SIGNAL('textEdited(const QString &)'), self.quit_on_type)

        list_view = QtGui.QListWidget()
        list_view.addItem('Double click')
        list_view.setFixedSize(80, 100)
        list_view.setFont(QtGui.QFont(font_family, font_size))
        #list_view.setStyleSheet('QPushButton { font-family: Helvetica; font-size: 10pt; }')
        self.connect(list_view, QtCore.SIGNAL("itemDoubleClicked (QListWidgetItem *)"), QtGui.qApp.quit)

        right_click_view = QtGui.QListWidget()
        right_click_view.setFixedSize(80, 100)
        right_click_view.setFont(QtGui.QFont(font_family, font_size))
        right_click_view.addItem('Contextmenu')

        right_click_view.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu);

        quit_action = QtGui.QAction("Quit", self)
        quit_action.setFont(QtGui.QFont(font_family, font_size))
        right_click_view.addAction(quit_action)
        quit_action.triggered.connect(QtGui.qApp.quit)

        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addWidget(button_click)
        #vbox.setAlignment(button_click, QtCore.Qt.AlignVCenter)
        vbox.addWidget(text_type)
        #vbox.setAlignment(text_type, QtCore.Qt.AlignVCenter)

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addLayout(vbox)
        hbox.addWidget(list_view)
        hbox.addWidget(right_click_view)

        self.setLayout(hbox)
        self.resize(300, 100)

        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('cleanlooks'))

    def quit_on_type(self):
        sender = self.sender()
        #print sender, sender.text()
        if sender.text() == "quit":
            self.close()


some_controls = ControlsWithLayout()
some_controls.show()

sys.exit(app.exec_())
