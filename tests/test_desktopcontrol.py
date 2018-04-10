#!/usr/bin/python
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
import shutil
import unittest
import subprocess
import common_test

# TODO: these tests are done only on the simplest backend
# since we need special setup for the rest
from desktopcontrol import *
from region import Region
from config import GlobalConfig


class DesktopControlTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_call(("vncserver", ":0", "-SecurityTypes", "None"),
                                  stdout=devnull, stderr=devnull)

    @classmethod
    def tearDownClass(self):
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_call(("vncserver", "-kill", ":0"),
                                  stdout=devnull, stderr=devnull)

    def setUp(self):
        # TODO: the Qemu DC backend is not fully developed
        self.backends = (AutoPyDesktopControl(), XDoToolDesktopControl(),
                         VNCDoToolDesktopControl())  # QemuDesktopControl()

    def tearDown(self):
        if os.path.exists(GlobalConfig.image_logging_destination):
            shutil.rmtree(GlobalConfig.image_logging_destination)

    def test_basic(self):
        for desktop in self.backends:
            self.assertTrue(desktop.width > 0)
            self.assertTrue(desktop.height > 0)

    def test_capture(self):
        for desktop in self.backends:
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
        for desktop in self.backends:
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
