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

import os
import shutil
import unittest
import common_test

# TODO: these tests are done only on the simplest backend
# since we need special setup for the rest
from desktopcontrol import AutoPyDesktopControl
from region import Region
from settings import GlobalSettings


class DesktopControlTest(unittest.TestCase):

    def tearDown(self):
        if os.path.exists(GlobalSettings.image_logging_destination):
            shutil.rmtree(GlobalSettings.image_logging_destination)

    def test_basic(self):
        desktop = AutoPyDesktopControl()

        self.assertTrue(desktop.width > 0)
        self.assertTrue(desktop.height > 0)

    def test_capture(self):
        desktop = AutoPyDesktopControl()
        screen_width = desktop.width
        screen_height = desktop.height

        # Fullscreen capture
        captured = desktop.capture_screen()
        self.assertEquals(screen_width, captured.width)
        self.assertEquals(screen_height, captured.height)

        # Capture with coordiantes
        captured = desktop.capture_screen(20, 10, screen_width / 2, screen_height / 2)
        self.assertEquals(screen_width / 2, captured.width)
        self.assertEquals(screen_height / 2, captured.height)

        # Capture with Region
        region = Region(10, 10, 320, 200)
        captured = desktop.capture_screen(region)
        self.assertEquals(320, captured.width)
        self.assertEquals(200, captured.height)

    def test_capture_clipping(self):
        desktop = AutoPyDesktopControl()
        screen_width = desktop.width
        screen_height = desktop.height

        captured = desktop.capture_screen(0, 0, 80000, 40000)
        self.assertEquals(screen_width, captured.width)
        self.assertEquals(screen_height, captured.height)

        captured = desktop.capture_screen(60000, 50000, 80000, 40000)
        self.assertEquals(1, captured.width)
        self.assertEquals(1, captured.height)

if __name__ == '__main__':
    unittest.main()
