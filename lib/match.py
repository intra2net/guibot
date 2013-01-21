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
import logging

# interconnected classes - import only their modules
# to avoid circular reference
import region

from image import Image
from location import Location

class Match:
    def __init__(self, xpos, ypos, image):
        self.xpos = xpos
        self.ypos = ypos
        self.width = image.get_width()
        self.height = image.get_height()

        target_offset = image.get_target_offset()
        self.target = self.calc_click_point(xpos, ypos, self.width, self.height, target_offset)

    def calc_click_point(self, xpos, ypos, width, height, offset):
        center_region = region.Region(0, 0, width, height)
        click_center = center_region.get_center()

        target_xpos = xpos + click_center.get_x() + offset.get_x()
        target_ypos = ypos + click_center.get_y() + offset.get_y()

        return Location(target_xpos, target_ypos)

    def get_target(self):
        return self.target
