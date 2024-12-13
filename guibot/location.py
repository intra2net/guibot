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

"""
Simple class to hold screen location data.

SUMMARY
------------------------------------------------------

..note:: Unless this class becomes more useful for the extra OOP abstraction
it might get deprecated in favor of a simple (x, y) tuple.

INTERFACE
------------------------------------------------------

"""


class Location(object):
    """Simple location on a 2D surface, region, or screen."""

    def __init__(self, xpos: int = 0, ypos: int = 0) -> None:
        """
        Build a location object.

        :param xpos: x coordinate of the location
        :param ypos: y coordinate of the location
        """
        self._xpos = xpos
        self._ypos = ypos

    def __str__(self) -> str:
        """Provide a compact form for the location."""
        return "(%s, %s)" % (self._xpos, self._ypos)

    def get_x(self) -> int:
        """
        Getter for readonly attribute.

        :returns: x coordinate of the location
        """
        return self._xpos

    x = property(fget=get_x)

    def get_y(self) -> int:
        """
        Getter for readonly attribute.

        :returns: y coordinate of the location
        """
        return self._ypos

    y = property(fget=get_y)

    def get_coords(self) -> tuple[int, int]:
        """
        Getter for readonly attributes.

        :returns: tuple of (x, y) coordinates of the location
        """
        return self._xpos, self._ypos

    coords = property(fget=get_coords)
