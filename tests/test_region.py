#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch and Plamen Dimitrov
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
import unittest
import time
import subprocess
import common_test

from imagepath import ImagePath
from location import Location
from region import Region
from match import Match
from desktopcontrol import DesktopControl
from image import Image
from errors import *

class RegionTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))
        self.imagepath.add_path(os.path.join(common_test.examples_dir, 'images'))

        self.script_show_picture = os.path.join(common_test.unittest_dir, 'show_picture.py')
        self.script_qt4_guitest = os.path.join(common_test.unittest_dir, 'qt4_guitest.py')

    def setUp(self):
        self.child_show_picture = None

    def tearDown(self):
        self.close_windows()

    def test_basic(self):
        screen_width = DesktopControl().get_width()
        screen_height = DesktopControl().get_height()

        region = Region()
        self.assertEqual(0, region.get_x())
        self.assertEqual(0, region.get_y())
        self.assertEqual(screen_width, region.get_width())
        self.assertEqual(screen_height, region.get_height())

        region = Region(10, 20, 300, 200)
        self.assertEqual(10, region.get_x())
        self.assertEqual(20, region.get_y())
        self.assertEqual(300, region.get_width())
        self.assertEqual(200, region.get_height())

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

    def show_image(self, filename):
        filename = self.imagepath.search(filename)

        self.child_show_picture = subprocess.Popen(['python', self.script_show_picture, filename])

    def close_windows(self):
        if self.child_show_picture is not None:
            self.child_show_picture.terminate()
            self.wait_end(self.child_show_picture)
            self.child_show_picture = None

            # Hack to make sure app is really closed
            time.sleep(0.5)

    def test_find(self):
        self.show_image('all_shapes')

        region = Region()
        match = region.find(Image('shape_blue_circle'))

        self.assertEqual(165, match.get_width())
        self.assertEqual(151, match.get_height())

        # Match again - this time just pass a filename
        match = region.find('shape_pink_box')
        self.assertEqual(69, match.get_width())
        self.assertEqual(48, match.get_height())

        # Test get_last_match()
        last_match = region.get_last_match()
        self.assertEqual(last_match.get_x(), match.get_x())
        self.assertEqual(last_match.get_y(), match.get_y())
        self.assertEqual(last_match.get_width(), match.get_width())
        self.assertEqual(last_match.get_height(), match.get_height())

    def test_find_target_offset(self):
        self.show_image('all_shapes.png')

        match = Region().find(Image('shape_blue_circle.png'))

        # Positive target offset
        match_offset = Region().find(Image('shape_blue_circle.png').target_offset(200, 100))
        self.assertEqual(match.get_target().get_x() + 200, match_offset.get_target().get_x())
        self.assertEqual(match.get_target().get_y() + 100, match_offset.get_target().get_y())

        # Positive target offset
        match_offset = Region().find(Image('shape_blue_circle.png').target_offset(-50, -30))
        self.assertEqual(match.get_target().get_x() - 50, match_offset.get_target().get_x())
        self.assertEqual(match.get_target().get_y() - 30, match_offset.get_target().get_y())

    def test_find_error(self):
        try:
            Region().find(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

        try:
            Region().find_all(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

    def test_zero_matches(self):
        self.show_image('all_shapes')

        matches = Region().find_all(Image('shape_blue_circle'))
        self.assertEqual(len(matches), 1)

        self.close_windows()

        matches = Region().find_all(Image('shape_blue_circle'), allow_zero = True)
        self.assertEqual(len(matches), 0)

        self.close_windows()

    def test_find_all(self):
        self.show_image('all_shapes')
        region = Region()
        # TODO: find should consider both autopy
        # and OpenCV but both may not be supported
        # at developer's platform
        #region.imagefinder = ImageFinder()

        matches = region.find_all(Image('shape_green_box'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(67, matches[0].get_width())
        self.assertEqual(52, matches[0].get_height())

        matches = region.find_all(Image('shape_red_box'))
        self.assertEqual(len(matches), 3)
        for match in matches:
            region.hover(match)
            time.sleep(0.5)
            self.assertEqual(68, match.get_width())
            self.assertEqual(56, match.get_height())

        # pink is similar to red, so the best fuzzy matches are
        # the three red boxes when considering color
        matches = region.find_all(Image('shape_pink_box').similarity(0.5))
        self.assertEqual(len(matches), 4)
        for match in matches:
            region.hover(match)
            time.sleep(0.5)
            self.assertEqual(69, match.get_width())
            self.assertEqual(48, match.get_height())

        # ignore colors here so the best matches for the pink box
        # should be based on shape (the green and yellow box)
        matches = region.find_all(Image('shape_pink_box'), nocolor = True)
        self.assertEqual(len(matches), 3)
        for match in matches:
            region.hover(match)
            time.sleep(0.5)
            self.assertEqual(69, match.get_width())
            self.assertEqual(48, match.get_height())

    def test_exists(self):
        self.show_image('all_shapes')

        match = Region().find(Image('shape_blue_circle'))
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

        match = Region().exists(Image('shape_blue_circle'))
        self.assertEqual(None, match)

        self.close_windows()

        # TODO: Own unit test for wait_vanish()
        self.assertTrue(Region().wait_vanish('all_shapes'))

    def test_wait_vanish(self):
        self.show_image('all_shapes')
        time.sleep(5)
        self.assertFalse(Region().wait_vanish('all_shapes', timeout = 5))

        self.close_windows()
        self.assertTrue(Region().wait_vanish('all_shapes', timeout = 10))

        self.close_windows()

    def test_hover(self):
        # Hover over Location
        self.show_image('all_shapes')
        region = Region()
        match = region.find(Image('shape_blue_circle'))
        match.hover(match.get_target())

        # Hover over Image with 50% similarity
        region.hover(Image('shape_pink_box').similarity(0.5))

        self.close_windows()

        # Test hovering over projected location
        self.show_image('h_ibs_viewport')
        # TODO: currently the match similarity is very low although
        # the image if matched properly - need to find a way to increase
        # the similarity while preserving the robustness of the feature matching
        region.configure_find(find_image = "features")
        match = region.find(Image('n_ibs').similarity(0.3))
        Region().hover(match.get_target())

    def test_click(self):
        # TODO: Fix openCV image finder first
        return

        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        Region().click('qt4gui_button')
        Region().wait_vanish('qt4gui_button')

        self.assertEqual(0, self.wait_end(child_pipe))

    def test_right_click(self):
        # TODO: Fix openCV image finder first
        return

        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        Region().right_click('qt4gui_contextmenu_label').nearby(200).click('qt4gui_contextmenu_quit')

        self.assertEqual(0, self.wait_end(child_pipe))

    def test_double_click(self):
        # TODO: Fix openCV image finder first
        return

        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        Region().double_click(Image('qt4gui_double_click').target_offset(0,-10))

        self.assertEqual(0, self.wait_end(child_pipe))

    def test_get_mouse_location(self):
        Region().hover(Location(0,0))

        pos = Region().get_mouse_location()
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.get_x() < 5)
        self.assertTrue(pos.get_y() < 5)

        Region().hover(Location(30,20))

        pos = Region().get_mouse_location()
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.get_x() > 25 and pos.get_x() < 35)
        self.assertTrue(pos.get_y() > 15 and pos.get_y() < 25)

# TODO: Write tests for:
# wait()
# wait_vanish()
#
# PyQt GUI based:
# drag_drop()
# drag()
# drop()
# mouse_down()
# mouse_up()
# type_text()
# press()

if __name__ == '__main__':
    unittest.main()
