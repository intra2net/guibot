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

import sys
from PyQt5 import QtGui, QtWidgets, QtCore


app = QtWidgets.QApplication(sys.argv)


class ImageWithLayout(QtWidgets.QWidget):

    def __init__(self, filename: str, title: str = "show_picture", parent: QtWidgets.QWidget = None) -> None:
        QtWidgets.QWidget.__init__(self, parent)

        self.setWindowTitle(title)

        image = QtWidgets.QLabel(self)
        image.setPixmap(QtGui.QPixmap(filename))

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(image)
        vbox.setAlignment(QtCore.Qt.AlignTop)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(vbox)
        hbox.setAlignment(QtCore.Qt.AlignLeft)

        self.setLayout(hbox)
        self.showFullScreen()

        self.setStyleSheet('ImageWithLayout { background: #ffffff; }')

if __name__ == "__main__":
    some_image = ImageWithLayout(*sys.argv[1:])
    some_image.show()
    sys.exit(app.exec_())
