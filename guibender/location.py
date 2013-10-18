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
class Location:
    def __init__(self, x_pos, y_pos):
        self.xpos = x_pos
        self.ypos = y_pos

    def __str__(self):
        return "(%s, %s)" % (self.xpos, self.ypos)

    def get_x(self):
        return self.xpos

    def get_y(self):
        return self.ypos
