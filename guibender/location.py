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
    """Simple location on a 2D surface, region, or screen."""

    def __init__(self, x_pos=0, y_pos=0):
        """
        Build a location object.

        :param int x_pos: x coordinate of the location
        :param int y_pos: y coordinate of the location
        """
        self.xpos = x_pos
        self.ypos = y_pos

    def __str__(self):
        """Provide a compact form for the location."""
        return "(%s, %s)" % (self.xpos, self.ypos)

    def get_x(self):
        """
        Getter for readonly attribute.

        :returns: x coordinate of the location
        :rtype: int
        """
        return self.xpos

    def get_y(self):
        """
        Getter for readonly attribute.

        :returns: y coordinate of the location
        :rtype: int
        """
        return self.ypos
