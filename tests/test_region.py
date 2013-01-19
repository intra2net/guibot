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
import sys
sys.path.append('../lib')

from region import Region
from screen import Screen

class RegionTest(unittest.TestCase):
    def test_basic(self):
        screen = Screen()

        region = Region()
        self.assertEqual(0, region.get_x())
        self.assertEqual(0, region.get_y())
        self.assertEqual(screen.get_width(), region.get_width())
        self.assertEqual(screen.get_height(), region.get_height())

        region = Region(10, 20, 300, 200)
        self.assertEqual(10, region.get_x())
        self.assertEqual(20, region.get_y())
        self.assertEqual(300, region.get_width())
        self.assertEqual(200, region.get_height())

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
        screen = Screen()

        region = Region(0, 0, 80000, 40000)
        self.assertEqual(screen.get_width(), region.get_width())
        self.assertEqual(screen.get_height(), region.get_height())

        region = Region(80000, 40000, 300, 200)
        self.assertEqual(screen.get_width() - 1, region.get_x())
        self.assertEqual(screen.get_height() - 1, region.get_y())
        self.assertEqual(1, region.get_width())
        self.assertEqual(1, region.get_height())

        region = Region(200, 100, screen.get_width() * 2, screen.get_height() * 2)
        self.assertEqual(200, region.get_x())
        self.assertEqual(100, region.get_y())
        self.assertEqual(screen.get_width() - region.get_x(), region.get_width())
        self.assertEqual(screen.get_height() - region.get_y(), region.get_height())

    def test_nearby(self):
        # TODO
        pass

    def test_above(self):
        # TODO
        pass

    def test_below(self):
        # TODO
        pass

    def test_left(self):
        # TODO
        pass

    def test_right(self):
        # TODO
        pass

if __name__ == '__main__':
    unittest.main()
