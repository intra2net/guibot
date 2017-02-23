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
import pprint

import common_test
from imagefinder import FeatureMatcher
from calibrator import Calibrator
from imagepath import ImagePath
from image import Image
from errors import *


class CalibratorTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))

    def calibration_setUp(self, needle, haystack, calibrate_backends):
        finder = FeatureMatcher()
        finder.imglog.logging_level = 10
        finder.eq.configure_backend(find_image="feature")
        for category in calibrate_backends:
            finder.eq.can_calibrate(True, category)
        calibrator = Calibrator()

        haystack = Image(haystack)
        needle = Image(needle)

        error = calibrator.calibrate(haystack, needle, finder)
        # print os.path.basename(needle.filename), os.path.basename(haystack.filename), error
        return error

    def test_calibrate_viewport(self):
        raw_error = self.calibration_setUp('n_ibs', 'h_ibs_viewport', [])
        cal_error = self.calibration_setUp('n_ibs', 'h_ibs_viewport',
                                           ["find", "fmatch"])

        self.assertLessEqual(cal_error, raw_error,
                             "Match error after calibration must be "
                             "less than the error before calibration")

    def test_calibrate_rotation(self):
        raw_error = self.calibration_setUp('n_ibs', 'h_ibs_rotated', [])
        cal_error = self.calibration_setUp('n_ibs', 'h_ibs_rotated',
                                           ["find", "fmatch"])

        self.assertLessEqual(cal_error, raw_error,
                             "Match error after calibration must be "
                             "less than the error before calibration")

    def test_calibrate_scaling(self):
        raw_error = self.calibration_setUp('n_ibs', 'h_ibs_scaled', [])
        cal_error = self.calibration_setUp('n_ibs', 'h_ibs_scaled',
                                           ["find", "fmatch"])

        self.assertLessEqual(cal_error, raw_error,
                             "Match error after calibration must be "
                             "less than the error before calibration")

    def test_benchmark_full_match(self):
        # TODO: check this test after improving the calibrator
        return
        haystack = Image('all_shapes')
        needle = Image('all_shapes')

        finder = ImageFinder()
        calibrator = Calibrator()

        results = calibrator.benchmark(haystack, needle, finder, calibration=False)
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "The benchmarked methods "
                           "should be more than one for the blue circle")
        # yes, some methods certainly don't work well together to
        # have similarity as low as 30% on a 1-to-1 match, but oh well...
        top_results = results[:-15]
        for result in top_results:
            # print result[1]
            self.assertGreaterEqual(result[1], 0.9,
                                    "Minimum similarity for full match is 0.5")

    def test_benchmark_feature_poor_image(self):
        haystack = Image('all_shapes')
        needle = Image('shape_blue_circle')

        finder = ImageFinder()
        calibrator = Calibrator()

        results = calibrator.benchmark(haystack, needle, finder, calibration=False)
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "The benchmarked methods "
                           "should be more than one for the blue circle")
        top_results = results[:3]
        for result in top_results:
            self.assertRegexpMatches(result[0], "\w+_\w+[_gray]?",
                                     "Template matching methods should be on the top")

    def test_benchmark_viewport_image(self):
        # TODO: check this test after improving the calibrator
        return
        haystack = Image('h_ibs_viewport')
        needle = Image('n_ibs')

        finder = ImageFinder()
        calibrator = Calibrator()

        results = calibrator.benchmark(haystack, needle, finder, calibration=False)
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "The benchmarked methods "
                           "should be more than one for the blue circle")
        top_results = results[:3]
        for result in top_results:
            self.assertRegexpMatches(result[0], "\w+-\w+-\w+",
                                     "Feature matching methods should be on the top")


if __name__ == '__main__':
    unittest.main()
