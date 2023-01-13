#!/usr/bin/python3
# Copyright 2013-2018 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

import sys, os
from PyQt5 import QtGui, QtWidgets, QtCore


import common_test


app = QtWidgets.QApplication(sys.argv)


class ControlsWithLayout(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.setWindowTitle('guibot test application')

        font_family = 'Helvetica'
        font_size = 10

        button_click = QtWidgets.QPushButton("close on click")
        button_click.setFixedSize(120, 30)
        button_click.setStyleSheet('QPushButton { font-family: ' + font_family + '; font-size: ' + str(font_size) + 't; }')
        button_click.clicked.connect(QtWidgets.qApp.quit)

        line_edit = QtWidgets.QLineEdit()
        line_edit.setPlaceholderText('type quit')
        line_edit.setFixedSize(120, 30)
        line_edit.textEdited.connect(self.quit_on_type)

        line_edit2 = QtWidgets.QLineEdit()
        line_edit2.setPlaceholderText('type anything')
        line_edit2.setFixedSize(120, 30)
        line_edit2.editingFinished.connect(QtWidgets.qApp.quit)

        text_edit = QtWidgets.QTextEdit('quit')
        cursor = text_edit.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(4, QtGui.QTextCursor.KeepAnchor)
        text_edit.setTextCursor(cursor)
        text_edit.setFixedSize(120, 30)
        text_edit.setAcceptDrops(True)

        list_view = QtWidgets.QListWidget()
        list_view.addItem('double click')
        list_view.setFixedSize(120, 130)
        list_view.setFont(QtGui.QFont(font_family, font_size))
        #list_view.setStyleSheet('QPushButton { font-family: Helvetica; font-size: 10pt; }')
        list_view.itemDoubleClicked.connect(QtWidgets.qApp.quit)

        right_click_view = QtWidgets.QListWidget()
        right_click_view.setFixedSize(120, 130)
        right_click_view.setFont(QtGui.QFont(font_family, font_size))
        right_click_view.addItem('contextmenu')
        right_click_view.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        quit_action = QtWidgets.QAction("close", self)
        quit_action.setFont(QtGui.QFont(font_family, font_size))
        right_click_view.addAction(quit_action)
        quit_action.triggered.connect(QtWidgets.qApp.quit)

        label1 = DragQuitLabel("drag to close", self)
        label1.setFixedSize(120, 30)
        label1.setStyleSheet('QLabel { font-family: ' + font_family + '; font-size: ' + str(font_size) + 't; }')
        label2 = DropQuitLabel("drop to close", self)
        label2.setFixedSize(120, 30)
        label2.setStyleSheet('QLabel { font-family: ' + font_family + '; font-size: ' + str(font_size) + 't; }')
        label3 = MouseDownQuitLabel("mouse down", self)
        label3.setFixedSize(120, 30)
        label3.setStyleSheet('QLabel { font-family: ' + font_family + '; font-size: ' + str(font_size) + 't; }')
        label4 = MouseUpQuitLabel("mouse up", self)
        label4.setFixedSize(120, 30)
        label4.setStyleSheet('QLabel { font-family: ' + font_family + '; font-size: ' + str(font_size) + 't; }')

        image1 = ImageQuitLabel(self)
        image1.setPixmap(QtGui.QPixmap(os.path.join(common_test.unittest_dir, "images/shape_red_box.png")))
        image2 = ImageChangeLabel(image1, self)
        image2.setPixmap(QtGui.QPixmap(os.path.join(common_test.unittest_dir, "images/shape_green_box.png")))
        self.changing_image = image2

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(button_click)
        vbox.addWidget(line_edit)
        vbox.addWidget(line_edit2)
        vbox.addWidget(text_edit)
        vbox.addStretch(1)
        vbox.setAlignment(QtCore.Qt.AlignTop)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(list_view)
        hbox.addWidget(right_click_view)
        hbox.setAlignment(QtCore.Qt.AlignTop)

        vbox2 = QtWidgets.QVBoxLayout()
        vbox2.addWidget(label1)
        vbox2.addWidget(label2)
        vbox2.addWidget(label3)
        vbox2.addWidget(label4)
        vbox2.addStretch(1)
        vbox2.setAlignment(QtCore.Qt.AlignTop)

        vbox3 = QtWidgets.QVBoxLayout()
        vbox3.addWidget(image1)
        vbox3.addWidget(image2)
        vbox3.addStretch(1)
        vbox3.setAlignment(QtCore.Qt.AlignTop)

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addLayout(vbox)
        hbox2.addLayout(hbox)
        hbox2.addLayout(vbox2)
        hbox2.addLayout(vbox3)
        hbox2.addStretch(1)
        hbox2.setAlignment(QtCore.Qt.AlignLeft)

        self.setLayout(hbox2)
        #self.resize(400, 100)
        self.showFullScreen()

        QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create('cleanlooks'))

    def quit_on_type(self):
        sender = self.sender()
        if sender.text() == "quit":
            self.close()

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.MiddleButton:
            self.close()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        elif e.key() == QtCore.Qt.Key_Shift:
            self.changing_image.setPixmap(QtGui.QPixmap(os.path.join(common_test.unittest_dir,
                                                                     "images/shape_black_box.png")))

    def closeEvent(self, e):
        self.close()


class DragQuitLabel(QtWidgets.QLabel):

    def __init__(self, title, parent):
        super(DragQuitLabel, self).__init__(title, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        self.parent().close()


class DropQuitLabel(QtWidgets.QLabel):

    def __init__(self, title, parent):
        super(DropQuitLabel, self).__init__(title, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('text/plain'):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        self.parent().close()


class MouseDownQuitLabel(QtWidgets.QLabel):

    def __init__(self, title, parent):
        super(MouseDownQuitLabel, self).__init__(title, parent)

    def mousePressEvent(self, e):
        self.parent().close()


class MouseUpQuitLabel(QtWidgets.QLabel):

    def __init__(self, title, parent):
        super(MouseUpQuitLabel, self).__init__(title, parent)
        # self.setAcceptDrops(True)

    def mouseReleaseEvent(self, e):
        self.parent().close()


class ImageQuitLabel(QtWidgets.QLabel):

    def __init__(self, parent):
        super(ImageQuitLabel, self).__init__(parent)

    def mousePressEvent(self, e):
        self.parent().close()


class ImageChangeLabel(QtWidgets.QLabel):

    def __init__(self, image, parent):
        super(ImageChangeLabel, self).__init__(parent)
        self.image = image

    def mousePressEvent(self, e):
        self.image.setPixmap(QtGui.QPixmap(os.path.join(common_test.unittest_dir,
                                                        "images/shape_black_box.png")))


if __name__ == "__main__":
    some_controls = ControlsWithLayout()
    some_controls.show()
    sys.exit(app.exec_())
