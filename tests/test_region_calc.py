#!/usr/bin/python3
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

import os
import unittest

import common_test
from guibot.region import Region
from guibot.controller import Controller, PyAutoGUIController


@unittest.skipIf(os.environ.get('DISABLE_PYAUTOGUI', "0") == "1", "PyAutoGUI disabled")
class RegionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = PyAutoGUIController()

    def test_position_calc(self) -> None:
        region = Region(10, 20, 300, 200)

        center = region.center
        self.assertEqual(160, center.x)
        self.assertEqual(120, center.y)

        top_left = region.top_left
        self.assertEqual(10, top_left.x)
        self.assertEqual(20, top_left.y)

        top_right = region.top_right
        self.assertEqual(310, top_right.x)
        self.assertEqual(20, top_right.y)

        bottom_left = region.bottom_left
        self.assertEqual(10, bottom_left.x)
        self.assertEqual(220, bottom_left.y)

        bottom_right = region.bottom_right
        self.assertEqual(310, bottom_right.x)
        self.assertEqual(220, bottom_right.y)

    def test_screen_clipping(self) -> None:
        screen = RegionTest.screen
        screen_width = screen.width
        screen_height = screen.height

        region = Region(0, 0, 80000, 40000)
        self.assertEqual(screen_width, region.width)
        self.assertEqual(screen_height, region.height)

        region = Region(80000, 40000, 300, 200)
        self.assertEqual(screen_width - 1, region.x)
        self.assertEqual(screen_height - 1, region.y)
        self.assertEqual(1, region.width)
        self.assertEqual(1, region.height)

        region = Region(200, 100, screen_width * 2, screen_height * 2)
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(screen_width - region.x, region.width)
        self.assertEqual(screen_height - region.y, region.height)

    def test_empty_screen_clipping(self) -> None:
        screen = Controller()
        screen_width = screen.width
        screen_height = screen.height
        self.assertEqual(screen_width, 0)
        self.assertEqual(screen_height, 0)

        region = Region(0, 0, 80000, 40000, dc=screen)
        self.assertEqual(region.width, 80000)
        self.assertEqual(region.height, 40000)

        region = Region(80000, 40000, 300, 200, dc=screen)
        self.assertEqual(region.x, 80000)
        self.assertEqual(region.y, 40000)
        self.assertEqual(region.width, 300)
        self.assertEqual(region.height, 200)

        region = Region(-300, -200, 300, 200, dc=screen)
        self.assertEqual(region.x, -300)
        self.assertEqual(region.y, -200)
        self.assertEqual(region.width, 300)
        self.assertEqual(region.height, 200)

    def test_nearby(self) -> None:
        screen = RegionTest.screen
        screen_width = screen.width
        screen_height = screen.height

        # defaults to 50 pixels
        region = Region(200, 100, 20, 10).nearby()
        self.assertEqual(150, region.x)
        self.assertEqual(50, region.y)
        self.assertEqual(120, region.width)
        self.assertEqual(110, region.height)

        region = Region(200, 100, 20, 10).nearby(rrange=80000)
        self.assertEqual(0, region.x)
        self.assertEqual(0, region.y)
        self.assertEqual(screen_width, region.width)
        self.assertEqual(screen_height, region.height)

        region = Region(200, 100, 20, 10).nearby(rrange=0)
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(20, region.width)
        self.assertEqual(10, region.height)

    def test_nearby_clipping(self) -> None:
        screen = RegionTest.screen
        screen_width = screen.width
        screen_height = screen.height

        # clip upper side
        region = Region(200, 100, 20, 10).nearby(rrange=150)
        self.assertEqual(50, region.x)
        self.assertEqual(0, region.y)
        self.assertEqual(320, region.width)
        self.assertEqual(260, region.height)

        # clip lower side
        region = Region(200, screen_height - 30, 20, 10).nearby(rrange=50)
        self.assertEqual(150, region.x)
        self.assertEqual(screen_height - 30 - 50, region.y)
        self.assertEqual(120, region.width)
        self.assertEqual(80, region.height)

        # clip left side
        region = Region(20, 100, 30, 10).nearby(rrange=50)
        self.assertEqual(0, region.x)
        self.assertEqual(50, region.y)
        self.assertEqual(100, region.width)
        self.assertEqual(110, region.height)

        # clip right side
        region = Region(screen_width - 30, 100, 20, 10).nearby(rrange=50)
        self.assertEqual(screen_width - 30 - 50, region.x)
        self.assertEqual(50, region.y)
        self.assertEqual(80, region.width)
        self.assertEqual(110, region.height)

    def test_above(self) -> None:
        region = Region(200, 100, 20, 10).above(50)
        self.assertEqual(200, region.x)
        self.assertEqual(50, region.y)
        self.assertEqual(20, region.width)
        self.assertEqual(60, region.height)

        region = Region(200, 100, 20, 10).above(80000)
        self.assertEqual(200, region.x)
        self.assertEqual(0, region.y)
        self.assertEqual(20, region.width)
        self.assertEqual(110, region.height)

        # extend to full screen above
        region = Region(200, 100, 20, 10).above()
        self.assertEqual(200, region.x)
        self.assertEqual(0, region.y)
        self.assertEqual(20, region.width)
        self.assertEqual(110, region.height)

    def test_below(self) -> None:
        screen_height = RegionTest.screen.height

        region = Region(200, 100, 20, 10).below(50)
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(20, region.width)
        self.assertEqual(60, region.height)

        region = Region(200, 100, 20, 10).below(80000)
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(20, region.width)
        self.assertEqual(screen_height - region.y, region.height)

        # extend to full screen below
        region = Region(200, 100, 20, 10).below()
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(20, region.width)
        self.assertEqual(screen_height - region.y, region.height)

    def test_left(self) -> None:
        region = Region(200, 100, 20, 10).left(50)
        self.assertEqual(150, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(70, region.width)
        self.assertEqual(10, region.height)

        region = Region(200, 100, 20, 10).left(80000)
        self.assertEqual(0, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(220, region.width)
        self.assertEqual(10, region.height)

        # extend to full screen above
        region = Region(200, 100, 20, 10).left()
        self.assertEqual(0, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(220, region.width)
        self.assertEqual(10, region.height)

    def test_right(self) -> None:
        screen_width = RegionTest.screen.width

        region = Region(200, 100, 20, 10).right(50)
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(70, region.width)
        self.assertEqual(10, region.height)

        region = Region(200, 100, 20, 10).right(80000)
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(screen_width - region.x, region.width)
        self.assertEqual(10, region.height)

        # extend to full screen above
        region = Region(200, 100, 20, 10).right()
        self.assertEqual(200, region.x)
        self.assertEqual(100, region.y)
        self.assertEqual(screen_width - region.x, region.width)
        self.assertEqual(10, region.height)

if __name__ == '__main__':
    unittest.main()
