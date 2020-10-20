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
from guibot.errors import *
from guibot.controller import *
from guibot.region import Region
from guibot.config import GlobalConfig


class ControllerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.vncpass = "test1234"

        os.environ["USER"] = os.environ.get("USER", "root")
        os.environ["HOME"] = os.environ.get("HOME", "/root")

        # create an Xauthority cookiefor the PyAutoGUI backend
        xauthfile = os.path.join(os.environ["HOME"], ".Xauthority")
        cls._dummy_xauth = False
        if not os.path.exists(xauthfile):
            cls._dummy_xauth = True
            with open(xauthfile, 'w') as file:
                pass

        # create the password file for the VNC server
        passfile = os.path.join(os.environ["HOME"], ".vnc/passwd")
        os.makedirs(os.path.dirname(passfile), exist_ok=True)
        if not os.path.isfile(passfile):
            subprocess.check_call(["x11vnc", "-q", "-storepasswd", cls.vncpass, passfile])

        # run the server in the background
        cls._server = subprocess.Popen(["x11vnc", "-q", "-forever", "-display",
                                        ":99", "-rfbauth", passfile])

    @classmethod
    def tearDownClass(cls):
        # kill the current server
        cls._server.terminate()
        vnc_config_dir = os.path.join(os.environ["HOME"], ".vnc")
        if os.path.exists(vnc_config_dir):
            shutil.rmtree(vnc_config_dir)
        xauthfile = os.path.join(os.environ["HOME"], ".Xauthority")
        if cls._dummy_xauth and os.path.exists(xauthfile):
            os.unlink(xauthfile)

    def setUp(self):
        self.backends = []
        if os.environ.get('DISABLE_AUTOPY', "0") == "0":
            self.backends += [AutoPyController()]
        self.backends += [XDoToolController(), PyAutoGUIController()]
        if os.environ.get('DISABLE_VNC', "0") == "0":
            vncdotool = VNCDoToolController(synchronize=False)
            vncdotool.params["vncdotool"]["vnc_password"] = self.vncpass
            vncdotool.synchronize_backend()
            self.backends += [vncdotool]
        # TODO: the Qemu DC backend is not fully developed
        # QemuController()

    def tearDown(self):
        if os.path.exists(GlobalConfig.image_logging_destination):
            shutil.rmtree(GlobalConfig.image_logging_destination)
        for display in self.backends:
            # disconnect any vncdotool backend
            if isinstance(display, VNCDoToolController):
                display._backend_obj.disconnect()

    def test_basic(self):
        for display in self.backends:
            self.assertTrue(display.width > 0)
            self.assertTrue(display.height > 0)

            self.assertIsNotNone(display.keymap)
            self.assertIsNotNone(display.mousemap)
            self.assertIsNotNone(display.modmap)

            location = display.mouse_location
            self.assertLessEqual(location.x, display.width)
            self.assertLessEqual(location.y, display.height)

    def test_single_backend(self):
        for display in self.backends:
            # the VNC controller has additional setup in these tests
            if isinstance(display, VNCDoToolController):
                continue

            display.configure_backend(reset=True)
            display.synchronize_backend(reset=True)
            self.assertIn("control", display.params)
            categories = set(display.params.keys())
            self.assertEqual(len(categories), 3)
            categories -= set(("type", "control"))
            category = categories.pop()

            self.assertIn("backend", display.params["control"])
            self.assertEqual(display.params["control"]["backend"], category)
            self.assertIn("backend", display.params[category])
            self.assertEqual(display.params[category]["backend"], "none")

            with self.assertRaises(UnsupportedBackendError):
                display.configure_backend(category="noncontrol")
            display.configure_backend(backend="ineffective", category=category)
            self.assertEqual(display.params[category]["backend"], "none")
            # cannot set inherited backends directly, only own categories
            with self.assertRaises(UnsupportedBackendError):
                display.configure_backend(backend=category, category="control")

            with self.assertRaises(UnsupportedBackendError):
                display.synchronize_backend(category="noncontrol")
            # no such backend has been configured so far
            with self.assertRaises(UninitializedBackendError):
                display.synchronize_backend(backend="ineffective", category=category)
            self.assertEqual(display.params[category]["backend"], "none")
            # cannot set inherited backends directly, only own categories
            with self.assertRaises(UnsupportedBackendError):
                display.synchronize_backend(backend=category, category="control")

    def test_capture(self):
        for display in self.backends:
            screen_width = display.width
            screen_height = display.height

            # Fullscreen capture
            captured = display.capture_screen()
            self.assertEqual(screen_width, captured.width)
            self.assertEqual(screen_height, captured.height)

            # Capture with coordinates
            captured = display.capture_screen(20, 10, int(screen_width/2), int(screen_height/2))
            self.assertEqual(int(screen_width/2), captured.width)
            self.assertEqual(int(screen_height/2), captured.height)

            # Capture with Region
            region = Region(10, 10, 320, 200)
            captured = display.capture_screen(region)
            self.assertEqual(320, captured.width)
            self.assertEqual(200, captured.height)

    def test_capture_clipping(self):
        for display in self.backends:
            screen_width = display.width
            screen_height = display.height

            captured = display.capture_screen(0, 0, 80000, 40000)
            self.assertEqual(screen_width, captured.width)
            self.assertEqual(screen_height, captured.height)

            captured = display.capture_screen(60000, 50000, 80000, 40000)
            self.assertEqual(1, captured.width)
            self.assertEqual(1, captured.height)

    def test_mouse_move(self):
        for display in self.backends:
            for is_smooth in [False, True]:
                display.mouse_move(Location(0, 0), smooth=is_smooth)
                location = display.mouse_location
                # some backends are not pixel perfect
                self.assertAlmostEqual(location.x, 0, delta=1)
                self.assertAlmostEqual(location.y, 0, delta=1)

                display.mouse_move(Location(30, 20), smooth=is_smooth)
                location = display.mouse_location
                # some backends are not pixel perfect
                self.assertAlmostEqual(location.x, 30, delta=1)
                self.assertAlmostEqual(location.y, 20, delta=1)


if __name__ == '__main__':
    unittest.main()
