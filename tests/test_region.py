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
import cv               # OpenCV
import time
sys.path.append('../lib')

from region import Region
from screen import Screen
from image import Image
from errors import *

class RegionTest(unittest.TestCase):
    def setUp(self):
        self.example_dir = '../examples/images/'

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
        image=cv.LoadImage(self.example_dir + filename, cv.CV_LOAD_IMAGE_COLOR)

        cv.ShowImage('test_region', image)
        # Process event loop
        for i in range(1, 100):
            cv.WaitKey(2)

    def close_windows(self):
        cv.DestroyAllWindows()
        # Process event loop
        for i in range(1, 100):
            cv.WaitKey(2)

    def test_find(self):
        self.show_image('all_shapes.png')

        # TODO: Implement/use image finder
        match = Region().find(Image(self.example_dir + 'shape_blue_circle.png'))

        self.assertEqual(165, match.get_width())
        self.assertEqual(151, match.get_height())

        self.close_windows()

    def test_find_error(self):
        try:
            Region().find(Image(self.example_dir + 'shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

if __name__ == '__main__':
    unittest.main()
