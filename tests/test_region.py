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
import shutil
import subprocess
import common_test

from settings import GlobalSettings
from imagepath import ImagePath
from location import Location
from region import Region
from match import Match
from image import Image, Text
from inputmap import Key
from imagefinder import *
from desktopcontrol import *
from errors import *


class RegionTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))

        self.script_img = os.path.join(common_test.unittest_dir, 'qt4_image.py')
        self.script_app = os.path.join(common_test.unittest_dir, 'qt4_application.py')

        # preserve values of static attributes
        self.prev_loglevel = GlobalSettings.image_logging_level
        self.prev_logpath = GlobalSettings.image_logging_destination
        GlobalSettings.image_logging_level = 0
        GlobalSettings.image_logging_destination = os.path.join(common_test.unittest_dir, 'tmp')

    @classmethod
    def tearDownClass(self):
        GlobalSettings.image_logging_level = self.prev_loglevel
        GlobalSettings.image_logging_destination = self.prev_logpath

    def setUp(self):
        self.child_img = None
        self.child_app = None

    def tearDown(self):
        self.close_windows()
        if os.path.exists(GlobalSettings.image_logging_destination):
            shutil.rmtree(GlobalSettings.image_logging_destination)

    def show_image(self, filename):
        filename = self.imagepath.search(filename)
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

    def test_basic(self):
        screen_width = AutoPyDesktopControl().width
        screen_height = AutoPyDesktopControl().height

        region = Region()
        self.assertEqual(0, region.x)
        self.assertEqual(0, region.y)
        self.assertEqual(screen_width, region.width)
        self.assertEqual(screen_height, region.height)

        region = Region(10, 20, 300, 200)
        self.assertEqual(10, region.x)
        self.assertEqual(20, region.y)
        self.assertEqual(300, region.width)
        self.assertEqual(200, region.height)

    def test_find(self):
        self.show_image('all_shapes')
        region = Region()

        match = region.find(Image('shape_green_box'))
        self.assertEqual((match.x, match.y), (30, 190))
        self.assertEqual(67, match.width)
        self.assertEqual(52, match.height)

        # Match again - this time just pass a filename
        match = region.find('shape_green_box')
        self.assertEqual((match.x, match.y), (30, 190))
        self.assertEqual(67, match.width)
        self.assertEqual(52, match.height)

        # Test last match property
        last_match = region.last_match
        self.assertEqual(last_match.x, match.x)
        self.assertEqual(last_match.y, match.y)
        self.assertEqual(last_match.width, match.width)
        self.assertEqual(last_match.height, match.height)

    def test_find_center_offset(self):
        self.show_image('all_shapes.png')

        match = Region().find(Image('shape_blue_circle.png'))

        # Positive target offset
        match_offset = Region().find(Image('shape_blue_circle.png').with_center_offset(200, 100))
        self.assertEqual(match.target.x + 200, match_offset.target.x)
        self.assertEqual(match.target.y + 100, match_offset.target.y)

        # Negative target offset
        match_offset = Region().find(Image('shape_blue_circle.png').with_center_offset(-50, -30))
        self.assertEqual(match.target.x - 50, match_offset.target.x)
        self.assertEqual(match.target.y - 30, match_offset.target.y)

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

    def test_find_all(self):
        self.show_image('all_shapes')
        # initialize template matching region to support multiple matches
        boxes = Region(cv=TemplateMatcher())

        greenbox = Image('shape_green_box')
        matches = boxes.find_all(greenbox)
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0].x, matches[0].y), (30, 190))
        self.assertEqual(67, matches[0].width)
        self.assertEqual(52, matches[0].height)

        redbox = Image('shape_red_box')
        matches = boxes.find_all(redbox)
        expected_matches = [(27, 25), (319, 27), (317, 116)]
        self.assertEqual(len(matches), len(expected_matches))
        for match in matches:
            Region().hover(match)
            time.sleep(0.5)
            self.assertIn((match.x, match.y), expected_matches)
            self.assertEqual(68, match.width)
            self.assertEqual(56, match.height)

        pinkbox = Image('shape_pink_box')
        # pink is similar to red, so the best fuzzy matches also
        # include the three red boxes when considering color
        boxes.cv_backend.params["find"]["similarity"].value = 0.5
        boxes.cv_backend.params["template"]["nocolor"].value = False
        matches = boxes.find_all(pinkbox)
        # approximately the above coordinates since maching different needle
        expected_matches = [(26, 36), (320, 38), (318, 127), (30, 255)]
        self.assertEqual(len(matches), len(expected_matches))
        for match in matches:
            boxes.hover(match)
            time.sleep(0.5)
            self.assertIn((match.x, match.y), expected_matches)
            self.assertEqual(69, match.width)
            self.assertEqual(48, match.height)

        # ignore colors here so the best matches for the pink box
        # should be based on shape (the green and yellow box)
        boxes.cv_backend.params["find"]["similarity"].value = 0.8
        boxes.cv_backend.params["template"]["nocolor"].value = True
        matches = boxes.find_all(pinkbox)
        expected_matches = [(28, 120), (31, 195), (30, 255)]
        self.assertEqual(len(matches), len(expected_matches))
        for match in matches:
            boxes.hover(match)
            time.sleep(0.5)
            self.assertIn((match.x, match.y), expected_matches)
            self.assertEqual(69, match.width)
            self.assertEqual(48, match.height)

    def test_find_zero_matches(self):
        self.show_image('all_shapes')
        # initialize template matching region to support multiple matches
        boxes = Region(cv=TemplateMatcher())

        matches = boxes.find_all(Image('shape_blue_circle'))
        self.assertEqual(len(matches), 1)
        self.close_windows()

        matches = boxes.find_all(Image('shape_blue_circle'), allow_zero=True)
        self.assertEqual(len(matches), 0)
        self.close_windows()

    def test_sample(self):
        self.show_image('all_shapes')

        # autopy matching does not support similarity
        shapes = Region(cv=AutoPyMatcher())
        similarity = shapes.sample(Image('shape_blue_circle'))
        self.assertEqual(similarity, 0.0)

        # initialize template matching region to support similarity
        shapes = Region(cv=TemplateMatcher())
        similarity = shapes.sample(Image('shape_blue_circle'))
        self.assertAlmostEqual(similarity, 0.999999, delta=0.001)

        shapes = Region(cv=HybridMatcher())
        similarity = shapes.sample(Image('shape_blue_circle'))
        self.assertEqual(similarity, 1.0)

        self.close_windows()

    def test_exists(self):
        self.show_image('all_shapes')

        match = Region().find(Image('shape_blue_circle'))
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

        match = Region().exists(Image('shape_blue_circle'))
        self.assertEqual(None, match)

    def test_wait(self):
        self.show_image('all_shapes')

        match = Region().wait(Image('shape_blue_circle'), timeout=5)
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

    def test_wait_vanish(self):
        self.show_image('all_shapes')

        self.assertRaises(NotFindError, Region().wait_vanish, 'all_shapes', timeout=10)

        self.close_windows()

        # assert no NotFindError is raised now
        self.assertTrue(Region().wait_vanish('all_shapes', timeout=10))

    def test_hover(self):
        self.show_image('all_shapes')

        region = Region()
        match = region.find(Image('shape_blue_circle'))
        region.hover(match.target)
        self.assertAlmostEqual(match.target.x, region.mouse_location.x, delta=1)
        self.assertAlmostEqual(match.target.y, region.mouse_location.y, delta=1)

        # hover over coordinates in a subregion
        match = match.find(Image('shape_blue_circle'))
        self.assertAlmostEqual(match.target.x, region.mouse_location.x, delta=1)
        self.assertAlmostEqual(match.target.y, region.mouse_location.y, delta=1)

        self.close_windows()

    def test_click(self):
        self.show_application()
        Region().click(Text("close on click"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_double_click(self):
        self.show_application()
        Region().idle(2).double_click(Text("double click"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_right_click(self):
        self.show_application()
        Region().right_click(Text("context menu")).nearby(100).idle(3).click(Text("close"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_press_keys(self):
        self.show_application()
        time.sleep(1)
        Region().press_keys(Region().ESC)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

        self.show_application()
        time.sleep(1)
        Region().press_keys([Region().ALT, Region().F4])
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_press_at(self):
        self.show_application()
        Region().press_at([Region().ESC], Text("type anything"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_text(self):
        self.show_application()
        # reset to (0,0) to avoid cursor on the same control (used many times)
        Region().hover(Location(0,0))
        Region().click(Text("type quit")).idle(0.2).type_text('quit')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_at(self):
        self.show_application()
        # reset to (0,0) to avoid cursor on the same control (used many times)
        Region().hover(Location(0,0))
        Region().type_at('quit', Text("type quit"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_drop(self):
        self.show_application()
        # the textedit is easy enough so that we don't need text matching
        Region().drag_drop('qt4gui_textedit', Text("type quit"))
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_from(self):
        self.show_application()

        # the textedit is easy enough so that we don't need text matching
        Region().drag_from('qt4gui_textedit')
        Region().hover(Text("drag to close"))

        # toggled buttons cleanup
        Region().dc_backend.mouse_up(Region().LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drop_at(self):
        self.show_application()

        # the textedit is easy enough so that we don't need text matching
        Region().drag_from('qt4gui_textedit')

        Region().drop_at(Text("drop to close"))

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_down(self):
        self.show_application()

        Region().idle(2).mouse_down(Text("mouse down"))

        # toggled buttons cleanup
        Region().dc_backend.mouse_up(Region().LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_up(self):
        self.show_application()

        # TODO: the GUI only works if mouse-up event is on the previous location
        # Region().mouse_down(Location(0,0))
        # Region().mouse_up(Text("mouse up"))
        match = Region().find(Text("mouse up"))
        Region().mouse_down(match.target)

        Region().mouse_up(match.target)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_get_mouse_location(self):
        Region().hover(Location(0, 0))

        pos = Region().mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.x < 5)
        self.assertTrue(pos.y < 5)

        Region().hover(Location(30, 20))

        pos = Region().mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.x > 25 and pos.x < 35)
        self.assertTrue(pos.y > 15 and pos.y < 25)


if __name__ == '__main__':
    unittest.main()
