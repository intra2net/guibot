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

# interconnected classes - import only their modules
# to avoid circular reference
import region

from location import Location


class Match(region.Region):
    """
    Wrapper around image which adds data necessary for manipulation
    of matches on a screen.
    """

    def __init__(self, xpos, ypos, image, dc=None, cv=None):
        """
        Build a match object.

        :param int xpos: x coordinate of the upleft vertex of the match region
        :param int ypos: y coordinate of the upleft vertex of the match region
        :param image: image that was matched
        :type image: :py:class:`image.Image`
        :param dc: DC backend used for the match if any
        :type dc: :py:class:`desktopcontrol.DesktopControl` or None
        :param cv: CV backend used for the match if any
        :type cv: :py:class:`imagefinder.ImageFinder` or None
        """
        super(Match, self).__init__(xpos, ypos, image.width, image.height, dc, cv)

        target_offset = image.target_center_offset
        self._target = self.calc_click_point(xpos, ypos, self._width, self._height, target_offset)

    def __str__(self):
        """Provide the target location of the match distinguishing it from any location."""
        # NOTE: the __str__ of the Location instance self._target is not called which is a hidden
        # (worst type of) error so call it explicitly here using str(self._target) or formatting
        return "%s (match)" % self._target

    def get_target(self):
        """
        Getter for readonly attribute.

        :returns: target location to click on if clicking on the match
        :rtype: :py:class:`location.Location`
        """
        return self._target
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
        center_region = region.Region(0, 0, width, height,
                                      dc=self.dc_backend, cv=self.cv_backend)
        click_center = center_region.center

        target_xpos = xpos + click_center.x + offset.x
        target_ypos = ypos + click_center.y + offset.y

        return Location(target_xpos, target_ypos)
