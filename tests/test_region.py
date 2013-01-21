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
import time
import subprocess
sys.path.append('../lib')

from region import Region
from match import Match
from screen import Screen
from image import Image
from errors import *

class RegionTest(unittest.TestCase):
    def setUp(self):
        self.example_dir = '../examples/images/'
        self.child_show_picture = None

    def tearDown(self):
        self.close_windows()

    def test_basic(self):
        screen_width = Screen().get_width()
        screen_height = Screen().get_height()

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

    def show_image(self, filename):
        self.child_show_picture = subprocess.Popen(['python', 'show_picture.py', self.example_dir + filename])

    def close_windows(self):
        if self.child_show_picture is not None:
            self.child_show_picture.kill()
            self.child_show_picture.wait()
            self.child_show_picture = None

    def test_find(self):
        self.show_image('all_shapes.png')

        # TODO: Implement/use image finder
        region = Region()
        match = region.find(Image(self.example_dir + 'shape_blue_circle.png'))

        self.assertEqual(165, match.get_width())
        self.assertEqual(151, match.get_height())

        # Match again - this time just pass a filename
        match = region.find(self.example_dir + 'shape_pink_box.png')
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

        match = Region().find(Image(self.example_dir + 'shape_blue_circle.png'))

        # Positive target offset
        match_offset = Region().find(Image(self.example_dir + 'shape_blue_circle.png').target_offset(200, 100))
        self.assertEqual(match.get_target().get_x() + 200, match_offset.get_target().get_x())
        self.assertEqual(match.get_target().get_y() + 100, match_offset.get_target().get_y())

        # Positive target offset
        match_offset = Region().find(Image(self.example_dir + 'shape_blue_circle.png').target_offset(-50, -30))
        self.assertEqual(match.get_target().get_x() - 50, match_offset.get_target().get_x())
        self.assertEqual(match.get_target().get_y() - 30, match_offset.get_target().get_y())

    def test_find_error(self):
        try:
            Region().find(Image(self.example_dir + 'shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

    def test_exists(self):
        self.show_image('all_shapes.png')

        match = Region().find(Image(self.example_dir + 'shape_blue_circle.png'))
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

        match = Region().exists(Image(self.example_dir + 'shape_blue_circle.png'))
        self.assertEqual(None, match)

        self.close_windows()

        # TODO: Own unit test for wait_vanish()
        self.assertTrue(Region().wait_vanish('all_shapes.png'))

    def test_hover(self):
        # Hover over Location
        self.show_image('all_shapes.png')
        match = Region().find(Image(self.example_dir + 'shape_blue_circle.png'))
        match.hover(match.get_target())

        # Hover over Image with 50% similarity
        Region().hover(Image(self.example_dir + 'shape_pink_box.png').similarity(0.5))

        # Hover over image filename
        Region().hover(self.example_dir + 'shape_green_box.png')

    def test_click(self):
        # TODO: Figure out script path relative to our own path
        child_pipe = subprocess.Popen(['python', 'qt4_guitest.py'])

        Region().click('images/qt4gui_button.png')
        Region().wait_vanish('images/qt4gui_button.png')

        self.assertEqual(0, child_pipe.wait())

    def test_right_click(self):
        # TODO: Figure out script path relative to our own path
        child_pipe = subprocess.Popen(['python', 'qt4_guitest.py'])

        Region().right_click('images/qt4gui_contextmenu_label.png').nearby(200).click('images/qt4gui_contextmenu_quit.png')

        # TODO: Wait timeout?
        self.assertEqual(0, child_pipe.wait())

    def test_double_click(self):
        # TODO: Figure out script path relative to our own path
        child_pipe = subprocess.Popen(['python', 'qt4_guitest.py'])

        Region().double_click(Image('images/qt4gui_double_click.png').target_offset(0,-10))

        # TODO: Wait timeout?
        self.assertEqual(0, child_pipe.wait())

# TODO: Also test: wait() and wait_vanish() via PyQT app

if __name__ == '__main__':
    unittest.main()
