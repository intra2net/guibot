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
import Location

class Region:
    def __init__(self, xpos=0, ypos=0, width=0, height=0):
        self.xpos = xpos
        self.ypos = ypos
        self.width = width
        self.height = height

    def get_x(self):
        return self.xpos

    def get_y(self):
        return self.ypos

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_center(self):
        xpos = (self.width - self.xpos) / 2
        ypos = (self.height - self.ypos) / 2

        return Location(xpos, ypos)

    def get_top_left(self):
        return Location(self.xpos, self.ypos)

    def get_top_right(self):
        return Location(self.xpos + self.width, self.ypos)

    def get_bottom_left(self):
        return Location(self.xpos, self.ypos + self.height)

    def get_bottom_right(self):
        return Location(self.xpos + self.width, self.ypos + self.height)
