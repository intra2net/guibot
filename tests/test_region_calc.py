#!/usr/bin/python
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

import unittest
import common_test

from region import Region
from desktopcontrol import DesktopControl


class RegionTest(unittest.TestCase):

    def test_position_calc(self):
        region = Region(10, 20, 300, 200)

        center = region.get_center()
        self.assertEqual(145, center.get_x())
        self.assertEqual(90, center.get_y())

        top_left = region.get_top_left()
        self.assertEqual(10, top_left.get_x())
        self.assertEqual(20, top_left.get_y())

        top_right = region.get_top_right()
        self.assertEqual(310, top_right.get_x())
        self.assertEqual(20, top_right.get_y())

        bottom_left = region.get_bottom_left()
        self.assertEqual(10, bottom_left.get_x())
        self.assertEqual(220, bottom_left.get_y())

        bottom_right = region.get_bottom_right()
        self.assertEqual(310, bottom_right.get_x())
        self.assertEqual(220, bottom_right.get_y())

    def test_screen_clipping(self):
        screen_width = DesktopControl().get_width()
        screen_height = DesktopControl().get_height()

        region = Region(0, 0, 80000, 40000)
        self.assertEqual(screen_width, region.get_width())
        self.assertEqual(screen_height, region.get_height())

        region = Region(80000, 40000, 300, 200)
        self.assertEqual(screen_width - 1, region.get_x())
        self.assertEqual(screen_height - 1, region.get_y())
        self.assertEqual(1, region.get_width())
        self.assertEqual(1, region.get_height())

        region = Region(200, 100, screen_width * 2, screen_height * 2)
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(screen_width - region.get_x(), region.get_width())
        self.assertEqual(screen_height - region.get_y(), region.get_height())

    def test_nearby(self):
        screen_width = DesktopControl().get_width()
        screen_height = DesktopControl().get_height()

        # defaults to 50 pixels
        region = Region(200, 100, 20, 10).nearby()
        self.assertEqual(150, region.get_x())
        self.assertEqual(50, region.get_y())
        self.assertEqual(120, region.get_width())
        self.assertEqual(110, region.get_height())

        region = Region(200, 100, 20, 10).nearby(rrange=80000)
        self.assertEqual(0, region.get_x())
        self.assertEqual(0, region.get_y())
        self.assertEqual(screen_width, region.get_width())
        self.assertEqual(screen_height, region.get_height())

        region = Region(200, 100, 20, 10).nearby(rrange=0)
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(20, region.get_width())
        self.assertEqual(10, region.get_height())

    def test_nearby_clipping(self):
        screen_width = DesktopControl().get_width()
        screen_height = DesktopControl().get_height()

        # clip upper side
        region = Region(200, 100, 20, 10).nearby(rrange=150)
        self.assertEqual(50, region.get_x())
        self.assertEqual(0, region.get_y())
        self.assertEqual(320, region.get_width())
        self.assertEqual(260, region.get_height())

        # clip lower side
        region = Region(200, screen_height - 30, 20, 10).nearby(rrange=50)
        self.assertEqual(150, region.get_x())
        self.assertEqual(screen_height - 30 - 50, region.get_y())
        self.assertEqual(120, region.get_width())
        self.assertEqual(80, region.get_height())

        # clip left side
        region = Region(20, 100, 30, 10).nearby(rrange=50)
        self.assertEqual(0, region.get_x())
        self.assertEqual(50, region.get_y())
        self.assertEqual(100, region.get_width())
        self.assertEqual(110, region.get_height())

        # clip right side
        region = Region(screen_width - 30, 100, 20, 10).nearby(rrange=50)
        self.assertEqual(screen_width - 30 - 50, region.get_x())
        self.assertEqual(50, region.get_y())
        self.assertEqual(80, region.get_width())
        self.assertEqual(110, region.get_height())

    def test_above(self):
        region = Region(200, 100, 20, 10).above(50)
        self.assertEqual(200, region.get_x())
        self.assertEqual(50, region.get_y())
        self.assertEqual(20, region.get_width())
        self.assertEqual(60, region.get_height())

        region = Region(200, 100, 20, 10).above(80000)
        self.assertEqual(200, region.get_x())
        self.assertEqual(0, region.get_y())
        self.assertEqual(20, region.get_width())
        self.assertEqual(110, region.get_height())

        # extend to full screen above
        region = Region(200, 100, 20, 10).above()
        self.assertEqual(200, region.get_x())
        self.assertEqual(0, region.get_y())
        self.assertEqual(20, region.get_width())
        self.assertEqual(110, region.get_height())

    def test_below(self):
        screen_height = DesktopControl().get_height()

        region = Region(200, 100, 20, 10).below(50)
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(20, region.get_width())
        self.assertEqual(60, region.get_height())

        region = Region(200, 100, 20, 10).below(80000)
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(20, region.get_width())
        self.assertEqual(screen_height - region.get_y(), region.get_height())

        # extend to full screen below
        region = Region(200, 100, 20, 10).below()
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(20, region.get_width())
        self.assertEqual(screen_height - region.get_y(), region.get_height())

    def test_left(self):
        region = Region(200, 100, 20, 10).left(50)
        self.assertEqual(150, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(70, region.get_width())
        self.assertEqual(10, region.get_height())

        region = Region(200, 100, 20, 10).left(80000)
        self.assertEqual(0, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(220, region.get_width())
        self.assertEqual(10, region.get_height())

        # extend to full screen above
        region = Region(200, 100, 20, 10).left()
        self.assertEqual(0, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(220, region.get_width())
        self.assertEqual(10, region.get_height())

    def test_right(self):
        screen_width = DesktopControl().get_width()

        region = Region(200, 100, 20, 10).right(50)
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(70, region.get_width())
        self.assertEqual(10, region.get_height())

        region = Region(200, 100, 20, 10).right(80000)
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(screen_width - region.get_x(), region.get_width())
        self.assertEqual(10, region.get_height())

        # extend to full screen above
        region = Region(200, 100, 20, 10).right()
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(screen_width - region.get_x(), region.get_width())
        self.assertEqual(10, region.get_height())

if __name__ == '__main__':
    unittest.main()
