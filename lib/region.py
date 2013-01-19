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
from location import Location
from screen import Screen

class Region:
    def __init__(self, xpos=0, ypos=0, width=0, height=0):
        self.screen = Screen()

        self.xpos = xpos
        self.ypos = ypos

        if width == 0:
            self.width = self.screen.get_width()
        else:
            self.width = width

        if height == 0:
            self.height = self.screen.get_height()
        else:
            self.height = height

        self._ensure_screen_clipping()

    def _ensure_screen_clipping(self):
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()

        if self.xpos < 0:
            self.xpos = 0

        if self.ypos < 0:
            self.ypos = 0

        if self.xpos > screen_width:
            self.xpos = screen_width -1

        if self.ypos > screen_height:
            self.ypos = screen_height -1

        if self.xpos + self.width > screen_width:
            self.width = screen_width - self.xpos

        if self.ypos + self.height > screen_height:
            self.height = screen_height - self.ypos

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

    def nearby(self, range=50):
        # TODO
        self._ensure_screen_clipping()

    def above(self, range=0):
        # TODO
        self._ensure_screen_clipping()

    def below(self, range=0):
        # TODO
        self._ensure_screen_clipping()

    def left(self, range=0):
        # TODO
        self._ensure_screen_clipping()

    def right(self, range=0):
        # TODO
        self._ensure_screen_clipping()
