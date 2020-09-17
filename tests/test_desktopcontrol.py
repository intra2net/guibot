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
import stat
import shutil
import unittest
import subprocess

import common_test
# TODO: these tests are done only on the simplest backend
# since we need special setup for the rest
from guibot.desktopcontrol import *
from guibot.region import Region
from guibot.config import GlobalConfig


@unittest.skipIf(os.environ.get('DISABLE_VNC', "0") == "1" or
                 os.environ.get('DISABLE_AUTOPY', "0") == "1",
                 "AutoPy or VNC disabled")
class DesktopControlTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.vncpass = "test1234"

        os.environ["USER"] = os.environ.get("USER", "root")
        os.environ["HOME"] = os.environ.get("HOME", "/root")

        # create the password file for the VNC server
        passfile = os.path.join(os.environ["HOME"], ".vnc/passwd")
        os.makedirs(os.path.dirname(passfile), exist_ok=True)
        if not os.path.isfile(passfile):
            subprocess.check_call(["x11vnc", "-q", "-storepasswd", cls.vncpass, passfile])

        # run the server in the background
        cls._server = subprocess.Popen([
            "x11vnc", "-q", "-forever", "-display", ":99", "-rfbauth", passfile])

    @classmethod
    def tearDownClass(cls):
        # kill the current server
        cls._server.terminate()
        vnc_config_dir = os.path.join(os.environ["HOME"], ".vnc")
        if os.path.exists(vnc_config_dir):
            shutil.rmtree(vnc_config_dir)

    def setUp(self):
        self.backends = [AutoPyDesktopControl(), XDoToolDesktopControl()]
        vncdotool = VNCDoToolDesktopControl(synchronize=False)
        vncdotool.params["vncdotool"]["vnc_password"] = self.vncpass
        vncdotool.synchronize_backend()
        self.backends += [vncdotool]
        # TODO: the Qemu DC backend is not fully developed
        # QemuDesktopControl()

    def tearDown(self):
        if os.path.exists(GlobalConfig.image_logging_destination):
            shutil.rmtree(GlobalConfig.image_logging_destination)
        for desktop in self.backends:
            # disconnect any vncdotool backend
            if isinstance(desktop, VNCDoToolDesktopControl):
                desktop._backend_obj.disconnect()

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
            self.assertEqual(screen_width, captured.width)
            self.assertEqual(screen_height, captured.height)

            # Capture with coordinates
            captured = desktop.capture_screen(20, 10, int(screen_width/2), int(screen_height/2))
            self.assertEqual(int(screen_width/2), captured.width)
            self.assertEqual(int(screen_height/2), captured.height)

            # Capture with Region
            region = Region(10, 10, 320, 200)
            captured = desktop.capture_screen(region)
            self.assertEqual(320, captured.width)
            self.assertEqual(200, captured.height)

    def test_capture_clipping(self):
        for desktop in self.backends:
            screen_width = desktop.width
            screen_height = desktop.height

            captured = desktop.capture_screen(0, 0, 80000, 40000)
            self.assertEqual(screen_width, captured.width)
            self.assertEqual(screen_height, captured.height)

            captured = desktop.capture_screen(60000, 50000, 80000, 40000)
            self.assertEqual(1, captured.width)
            self.assertEqual(1, captured.height)


if __name__ == '__main__':
    unittest.main()
