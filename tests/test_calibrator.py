#!/usr/bin/python
# Copyright 2013 Intranet AG / Plamen Dimitrov
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

import cv, cv2

import common_test


from imagefinder import ImageFinder
from calibrator import Calibrator
from imagepath import ImagePath
from image import Image
from errors import *

class CalibratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))
        self.imagepath.add_path(os.path.join(common_test.examples_dir, 'images'))
        self.imagepath.add_path(".")

        self.script_show_picture = os.path.join(common_test.unittest_dir, 'show_picture.py')

    def test_calibrate(self):
        finder = ImageFinder()
        finder.image_logging = 10
        finder.eq.can_calibrate(True, "find")
        finder.eq.can_calibrate(True, "fmatch")
        calibrator = Calibrator()

        haystack = Image('h_ibs_viewport')
        needle = Image('n_ibs')
        error = calibrator.calibrate(haystack, needle, finder)
        #print error
        self.assertLessEqual(error, 0.1, 'Match error after calibration must be "\
                         "less than 0.1 for this image')

        haystack = Image('h_ibs_rotated')
        needle = Image('n_ibs')
        error = calibrator.calibrate(haystack, needle, finder)
        #print error
        self.assertLessEqual(error, 0.4, 'Match error after calibration must be "\
                             "less than 0.4 for this image')

        haystack = Image('h_ibs_scaled')
        needle = Image('n_ibs')
        error = calibrator.calibrate(haystack, needle, finder)
        #print error
        self.assertLessEqual(error, 0.1, 'Match error after calibration must be "\
                             "less than 0.1 for this image')

    def test_benchmark(self):
        haystack = Image('all_shapes')
        needle = Image('all_shapes')

        finder = ImageFinder()
        calibrator = Calibrator()
        results = calibrator.benchmark(haystack, needle, finder, calibration = False)
        #print results
        self.assertGreater(len(results), 0, "The benchmarked methods "\
                           "should be more than one for the blue circle")

        haystack = Image('all_shapes')
        needle = Image('shape_blue_circle')
        results = calibrator.benchmark(haystack, needle, finder, calibration = False)
        #print results
        self.assertGreater(len(results), 0, "The benchmarked methods "\
                           "should be more than one for the blue circle")

        haystack = Image('h_ibs_viewport')
        needle = Image('n_ibs')
        results = calibrator.benchmark(haystack, needle, finder, calibration = False)
        #print results
        self.assertGreater(len(results), 0, "The benchmarked methods "\
                           "should be more than one for the blue circle")


if __name__ == '__main__':
    unittest.main()

