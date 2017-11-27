#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch and Plamen Dimitrov
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
#

import os
import unittest
import time
import shutil
import subprocess
import common_test

from config import GlobalConfig
from path import Path
from location import Location
from region import Region
from match import Match
from target import Image, Text
from inputmap import Key
from finder import *
from desktopcontrol import *
from errors import *


class RegionTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.path = Path()
        self.path.add_path(os.path.join(common_test.unittest_dir, 'images'))

        self.script_img = os.path.join(common_test.unittest_dir, 'qt4_image.py')
        self.script_app = os.path.join(common_test.unittest_dir, 'qt4_application.py')

        # preserve values of static attributes
        self.prev_loglevel = GlobalConfig.image_logging_level
        self.prev_logpath = GlobalConfig.image_logging_destination
        GlobalConfig.image_logging_level = 0
        GlobalConfig.image_logging_destination = os.path.join(common_test.unittest_dir, 'tmp')

    @classmethod
    def tearDownClass(self):
        GlobalConfig.image_logging_level = self.prev_loglevel
        GlobalConfig.image_logging_destination = self.prev_logpath

    def setUp(self):
        self.child_img = None
        self.child_app = None
        # initialize template matching region to support some minimal robustness
        GlobalConfig.hybrid_match_backend = "template"
        self.region = Region()

    def tearDown(self):
        self.close_windows()
        if os.path.exists(GlobalConfig.image_logging_destination):
            shutil.rmtree(GlobalConfig.image_logging_destination)

    def show_image(self, filename):
        filename = self.path.search(filename)
        self.child_img = subprocess.Popen(['python', self.script_img, filename])
        # HACK: avoid small variability in loading speed
        time.sleep(3)

    def show_application(self):
        self.child_app = subprocess.Popen(['python', self.script_app])
        # HACK: avoid small variability in loading speed
        time.sleep(3)

    def close_windows(self):
        if self.child_img is not None:
            self.child_img.terminate()
            self.wait_end(self.child_img)
            self.child_img = None

            # HACK: make sure app is really closed
            time.sleep(0.5)

        if self.child_app is not None:
            self.child_app.terminate()
            self.wait_end(self.child_app)
            self.child_app = None

            # HACK: make sure app is really closed
            time.sleep(0.5)

    def wait_end(self, subprocess_pipe, timeout=30):
        expires = time.time() + timeout

        while True:
            exit_code = subprocess_pipe.poll()
            if exit_code is not None:
                return exit_code

            if time.time() > expires:
                self.fail('Program did not close on time. Ignoring')
                break

            time.sleep(0.2)

    def test_hover(self):
        self.show_image('all_shapes')

        match = self.region.find(Image('shape_blue_circle'))
        self.region.hover(match.target)
        self.assertAlmostEqual(match.target.x, self.region.mouse_location.x, delta=1)
        self.assertAlmostEqual(match.target.y, self.region.mouse_location.y, delta=1)

        # hover over coordinates in a subregion
        match = match.find(Image('shape_blue_circle'))
        self.assertAlmostEqual(match.target.x, self.region.mouse_location.x, delta=1)
        self.assertAlmostEqual(match.target.y, self.region.mouse_location.y, delta=1)

        self.close_windows()

    def test_click(self):
        self.show_application()
        self.region.click(Text("close on click"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_double_click(self):
        self.show_application()
        self.region.idle(2).double_click(Text("double click"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_right_click(self):
        self.show_application()
        self.region.right_click(Text("context menu")).nearby(100).idle(3).click(Text("close"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_press_keys(self):
        self.show_application()
        time.sleep(1)
        self.region.press_keys(self.region.ESC)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

        self.show_application()
        time.sleep(1)
        self.region.press_keys([self.region.ALT, self.region.F4])
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_press_at(self):
        self.show_application()
        self.region.press_at([self.region.ESC], Text("type anything"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_text(self):
        self.show_application()
        # reset to (0,0) to avoid cursor on the same control (used many times)
        self.region.hover(Location(0,0))
        self.region.click(Text("type quit")).idle(0.2).type_text('quit')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_at(self):
        self.show_application()
        # reset to (0,0) to avoid cursor on the same control (used many times)
        self.region.hover(Location(0,0))
        self.region.type_at('quit', Text("type quit"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_drop(self):
        self.show_application()
        # the textedit is easy enough so that we don't need text matching
        self.region.drag_drop('qt4gui_textedit', Text("type quit"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_from(self):
        self.show_application()

        # the textedit is easy enough so that we don't need text matching
        self.region.drag_from('qt4gui_textedit')
        self.region.hover(Text("drag to close"))

        # toggled buttons cleanup
        self.region.dc_backend.mouse_up(self.region.LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drop_at(self):
        self.show_application()

        # the textedit is easy enough so that we don't need text matching
        self.region.drag_from('qt4gui_textedit')

        self.region.drop_at(Text("drop to close"))

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_down(self):
        self.show_application()

        self.region.idle(2).mouse_down(Text("mouse down"))

        # toggled buttons cleanup
        self.region.dc_backend.mouse_up(self.region.LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_up(self):
        self.show_application()

        # TODO: the GUI only works if mouse-up event is on the previous location
        # self.region.mouse_down(Location(0,0))
        # self.region.mouse_up(Text("mouse up"))
        match = self.region.find(Text("mouse up"))
        self.region.mouse_down(match.target)

        self.region.mouse_up(match.target)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_get_mouse_location(self):
        self.region.hover(Location(0, 0))

        pos = self.region.mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.x < 5)
        self.assertTrue(pos.y < 5)

        self.region.hover(Location(30, 20))

        pos = self.region.mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.x > 25 and pos.x < 35)
        self.assertTrue(pos.y > 15 and pos.y < 25)


if __name__ == '__main__':
    unittest.main()
