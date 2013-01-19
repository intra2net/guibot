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

from screen import Screen
from region import Region

class ScreenTest(unittest.TestCase):
    def test_basic(self):
        screen = Screen()

        self.assertTrue(screen.get_width() > 0)
        self.assertTrue(screen.get_height() > 0)

    def test_capture(self):
        screen = Screen()
        screen_width = screen.get_width()
        screen_height = screen.get_height()

        # Fullscreen capture
        captured = screen.capture()
        self.assertEquals(screen_width, captured.get_width())
        self.assertEquals(screen_height, captured.get_height())

        # Capture with coordiantes
        captured = screen.capture(20, 10, screen_width/2, screen_height/2)
        self.assertEquals(screen_width/2, captured.get_width())
        self.assertEquals(screen_height/2, captured.get_height())

        # Capture with Region
        region = Region(10, 10, 320, 200)
        captured = screen.capture(region)
        self.assertEquals(320, captured.get_width())
        self.assertEquals(200, captured.get_height())

    def test_capture_clipping(self):
        screen = Screen()
        screen_width = screen.get_width()
        screen_height = screen.get_height()

        captured = screen.capture(0, 0, 80000, 40000)
        self.assertEquals(screen_width, captured.get_width())
        self.assertEquals(screen_height, captured.get_height())

        captured = screen.capture(60000, 50000, 80000, 40000)
        self.assertEquals(1, captured.get_width())
        self.assertEquals(1, captured.get_height())

if __name__ == '__main__':
    unittest.main()
