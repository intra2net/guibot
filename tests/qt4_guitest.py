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

        line_edit = QtGui.QLineEdit()
        line_edit.setPlaceholderText('type "quit"')
        #line_edit.setAcceptDrops(True)
        line_edit.setFixedSize(100, 20)
        self.connect(line_edit, QtCore.SIGNAL('textEdited(const QString &)'), self.quit_on_type)

        line_edit2 = QtGui.QLineEdit()
        line_edit2.setPlaceholderText('type anything')
        #line_edit2.setAcceptDrops(True)
        line_edit2.setFixedSize(100, 20)
        self.connect(line_edit2, QtCore.SIGNAL('editingFinished()'), QtGui.qApp.quit)

        text_edit = QtGui.QTextEdit('quit')
        cursor = text_edit.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(4, QtGui.QTextCursor.KeepAnchor)
        text_edit.setTextCursor(cursor)
        text_edit.setFixedSize(100, 30)
        text_edit.setAcceptDrops(True)

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
        vbox.addWidget(line_edit)
        vbox.addWidget(line_edit2)
        vbox.addWidget(text_edit)

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

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()


some_controls = ControlsWithLayout()
some_controls.show()

sys.exit(app.exec_())
