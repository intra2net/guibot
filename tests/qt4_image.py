#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch
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
#

import sys
from PyQt4 import QtGui, QtCore


app = QtGui.QApplication(sys.argv)


class ImageWithLayout(QtGui.QWidget):

    def __init__(self, filename, title="show_picture", parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setWindowTitle(title)

        image = QtGui.QLabel(self)
        image.setPixmap(QtGui.QPixmap(filename))

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(image)
        vbox.setAlignment(QtCore.Qt.AlignTop)

        hbox = QtGui.QHBoxLayout()
        hbox.addLayout(vbox)
        hbox.setAlignment(QtCore.Qt.AlignLeft)

        self.setLayout(hbox)
        self.showFullScreen()

        self.setStyleSheet('ImageWithLayout { background: #ffffff; }')

if __name__ == "__main__":
    some_image = ImageWithLayout(*sys.argv[1:])
    some_image.show()
    sys.exit(app.exec_())
