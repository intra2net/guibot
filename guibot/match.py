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

from region import Region
from location import Location
from desktopcontrol import DesktopControl
from finder import Finder


class Match(Region):
    """
    Wrapper around image which adds data necessary for manipulation
    of matches on a screen.
    """

    def __init__(self, xpos, ypos, width, height, dx=0, dy=0,
                 similarity=0.0, dc=None, cv=None):
        """
        Build a match object.

        :param int xpos: x coordinate of the upleft vertex of the match region
        :param int ypos: y coordinate of the upleft vertex of the match region
        :param int width: x distance from upleft to downright vertex of the match region
        :param int height: y distance from upleft to downright vertex of the match region
        :param int dx: x offset from the center of the match region
        :param int dy: y offset from the center of the match region
        :param float similarity: attained similarity of the match region
        """
        dc = DesktopControl() if dc is None else dc
        cv = Finder() if cv is None else cv
        super(Match, self).__init__(xpos, ypos, width, height, dc=dc, cv=cv)
        # custom DC and CV backends can be set later on by a region
        # if a match within the match will be needed (they are optional)
        # -> recreate the match to fully initialized it with a different backend
        self._similarity = similarity
        self._dx, self._dy = dx, dy

    def __str__(self):
        """Provide the target location of the match distinguishing it from any location."""
        return "%s (match)" % self.target

    def set_x(self, value):
        """
        Setter for previously readonly attribute.

        Necessary to override match location in a subregion (displaced).

        :param value: x coordinate of the upleft vertex of the region
        :type value: int
        """
        self._xpos = value
    x = property(fget=Region.get_x, fset=set_x)

    def set_y(self, value):
        """
        Setter for previously readonly attribute.

        Necessary to override match location in a subregion (displaced).

        :param value: y coordinate of the upleft vertex of the region
        :type value: int
        """
        self._ypos = value
    y = property(fget=Region.get_y, fset=set_y)

    def get_dx(self):
        """
        Getter for readonly attribute.

        :returns: x offset from the center of the match region
        :rtype: int
        """
        return self._dx
    dx = property(fget=get_dx)

    def get_dy(self):
        """
        Getter for readonly attribute.

        :returns: y offset from the center of the match region
        :rtype: int
        """
        return self._dy
    dy = property(fget=get_dy)

    def get_similarity(self):
        """
        Getter for readonly attribute.

        :returns: similarity the match was obtained with
        :rtype: float
        """
        return self._similarity
    similarity = property(fget=get_similarity)

    def get_target(self):
        """
        Getter for readonly attribute.

        :returns: target location to click on if clicking on the match
        :rtype: :py:class:`location.Location`
        """
        return self.calc_click_point(self._xpos, self._ypos,
                                     self._width, self._height,
                                     Location(self._dx, self._dy))
    target = property(fget=get_target)

    def calc_click_point(self, xpos, ypos, width, height, offset):
        """
        Calculate target location to click on if clicking on the match.

        :param int xpos: x coordinate of upleft vertex of the match region
        :param int ypos: y coordinate of upleft vertex of the match region
        :param int width: width of the match region
        :param int height: height of the match region
        :param offset: offset from the match region center for the final target
        :type offset: :py:class:`location.Location`
        :returns: target location to click on if clicking on the match
        :rtype: :py:class:`location.Location`
        """
        center_region = Region(0, 0, width, height,
                               dc=self.dc_backend, cv=self.cv_backend)
        click_center = center_region.center

        target_xpos = xpos + click_center.x + offset.x
        target_ypos = ypos + click_center.y + offset.y

        return Location(target_xpos, target_ypos)
