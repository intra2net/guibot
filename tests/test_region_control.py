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

        # gui test scripts
        self.script_app = os.path.join(common_test.unittest_dir, 'qt4_application.py')

        # prefixed controls
        # NOTE: provide and use only fixed locations to avoid CV backend dependencies
        self.click_control = Location(75, 25)
        self.double_click_control = Location(185, 20)
        self.context_menu_control = Location(315, 20)
        self.context_menu_close_control = Location(355, 35)
        self.mouse_down_control = Location(435, 95)
        self.mouse_up_control = Location(435, 135)
        self.textedit_control = Location(35, 135)
        self.textedit_quit_control = Location(65, 60)
        self.textedit_any_control = Location(65, 95)
        self.drag_control = Location(435, 25)
        self.drop_control = Location(435, 65)

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
        self.child_app = None
        self.region = Region()

    def tearDown(self):
        self.close_windows()
        if os.path.exists(GlobalConfig.image_logging_destination):
            shutil.rmtree(GlobalConfig.image_logging_destination)

    def show_application(self):
        self.child_app = subprocess.Popen(['python', self.script_app])
        # HACK: avoid small variability in loading speed
        time.sleep(3)

    def close_windows(self):
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

    def test_get_mouse_location(self):
        self.region.hover(Location(0, 0))
        pos = self.region.mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertAlmostEqual(pos.x, 0, delta=1)
        self.assertAlmostEqual(pos.y, 0, delta=1)

        self.region.hover(Location(30, 20))
        pos = self.region.mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertAlmostEqual(pos.x, 30, delta=1)
        self.assertAlmostEqual(pos.y, 20, delta=1)

    def test_hover(self):
        self.show_application()

        match = self.region.find('shape_green_box')
        self.region.hover(match.target)
        self.assertAlmostEqual(match.target.x, self.region.mouse_location.x, delta=1)
        self.assertAlmostEqual(match.target.y, self.region.mouse_location.y, delta=1)

        # hover over coordinates in a subregion
        match = match.find('shape_green_box')
        self.assertAlmostEqual(match.target.x, self.region.mouse_location.x, delta=1)
        self.assertAlmostEqual(match.target.y, self.region.mouse_location.y, delta=1)

        self.close_windows()

    def test_click(self):
        self.show_application()
        self.region.click(self.click_control)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_right_click(self):
        self.show_application()
        self.region.right_click(self.context_menu_control)
        self.region.idle(3).click(self.context_menu_close_control)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_double_click(self):
        self.show_application()
        self.region.double_click(self.double_click_control)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_multi_click(self):
        self.show_application()
        self.region.multi_click(self.click_control, count=1)
        self.assertEqual(0, self.wait_end(self.child_app))

        self.show_application()
        self.region.multi_click(self.double_click_control, count=2)
        self.assertEqual(0, self.wait_end(self.child_app))

        self.child_app = None

    def test_click_expect(self):
        self.show_application()
        self.region.click_expect('shape_green_box')
        self.close_windows()

    def test_click_expect_different(self):
        self.show_application()
        self.region.click_expect('shape_green_box', 'shape_black_box')
        self.close_windows()

    def test_click_vanish(self):
        self.show_application()
        self.region.click_vanish('shape_red_box')
        self.close_windows()

    def test_click_vanish_different(self):
        self.show_application()
        self.region.click_vanish('shape_green_box', 'shape_red_box')
        self.close_windows()

    def test_click_at_index(self):
        self.show_application()
        self.region.click_at_index('shape_red_box', 0)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_down(self):
        self.show_application()

        self.region.mouse_down(self.mouse_down_control)

        # toggled buttons cleanup
        self.region.dc_backend.mouse_up(self.region.LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_up(self):
        self.show_application()

        # TODO: the GUI only works if mouse-up event is on the previous location
        # self.region.mouse_down(Location(0,0))
        # self.region.mouse_up(self.mouse_up_control)
        self.region.mouse_down(self.mouse_up_control)

        self.region.mouse_up(self.mouse_up_control)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_drop(self):
        self.show_application()
        self.region.drag_drop(self.textedit_control, self.textedit_quit_control)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_from(self):
        self.show_application()

        self.region.drag_from(self.textedit_control)
        self.region.hover(self.drag_control)

        # toggled buttons cleanup
        self.region.dc_backend.mouse_up(self.region.LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drop_at(self):
        self.show_application()

        self.region.drag_from(self.textedit_control)
        self.region.drop_at(self.drop_control)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    @unittest.expectedFailure  # fails on some platforms
    def test_press_keys(self):
        self.show_application()
        time.sleep(1)
        self.region.press_keys(self.region.ESC)
        self.assertEqual(0, self.wait_end(self.child_app))

        # BUG: Qt fails to register a close event in some cases
        self.show_application()
        time.sleep(1)
        self.region.press_keys([self.region.ALT, self.region.F4])
        self.assertEqual(0, self.wait_end(self.child_app))

        self.child_app = None

    def test_press_at(self):
        self.show_application()
        self.region.press_at([self.region.ESC], self.textedit_any_control)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_text(self):
        self.show_application()
        self.region.click(self.textedit_quit_control)
        self.region.idle(0.2).type_text('quit')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_at(self):
        self.show_application()
        self.region.type_at('quit', self.textedit_quit_control)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_fill_at(self):
        self.show_application()
        self.region.fill_at(self.textedit_quit_control, 'quit', 0, 0)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_select_at(self):
        self.show_application()
        self.region.right_click(self.context_menu_control)
        self.region.select_at(self.context_menu_close_control, 1, 0, 0, mark_clicks=0)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

if __name__ == '__main__':
    unittest.main()
