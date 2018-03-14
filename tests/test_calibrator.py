#!/usr/bin/python
# Copyright 2013 Intranet AG / Plamen Dimitrov
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
import pprint

import common_test
from calibrator import Calibrator
from path import Path
from finder import *
from target import *
from errors import *


class CalibratorTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.path = Path()
        self.path.add_path(os.path.join(common_test.unittest_dir, 'images'))

    def calibration_setUp(self, needle, haystack, calibrate_backends):
        finder = FeatureFinder()
        finder.imglog.logging_level = 10
        finder.configure()
        for category in calibrate_backends:
            finder.can_calibrate(category, True)

        haystack = Image(haystack)
        needle = Image(needle)
        calibrator = Calibrator(needle, haystack)

        error = calibrator.calibrate(finder)
        return error

    def test_calibrate_viewport(self):
        raw_similarity = self.calibration_setUp('n_ibs', 'h_ibs_viewport', [])
        cal_similarity = self.calibration_setUp('n_ibs', 'h_ibs_viewport',
                                                ["find", "feature", "fdetect",
                                                 "fextract", "fmatch"])

        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be "
                             "less than the similarity after calibration")

    def test_calibrate_rotation(self):
        raw_similarity = self.calibration_setUp('n_ibs', 'h_ibs_rotated', [])
        cal_similarity = self.calibration_setUp('n_ibs', 'h_ibs_rotated',
                                                ["find", "feature", "fdetect",
                                                 "fextract", "fmatch"])

        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be "
                             "less than the similarity after calibration")

    def test_calibrate_scaling(self):
        raw_similarity = self.calibration_setUp('n_ibs', 'h_ibs_scaled', [])
        cal_similarity = self.calibration_setUp('n_ibs', 'h_ibs_scaled',
                                                ["find", "feature", "fdetect",
                                                 "fextract", "fmatch"])

        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be "
                             "less than the similarity after calibration")

    def test_benchmark_autopy(self):
        calibrator = Calibrator(Image('shape_blue_circle'), Image('all_shapes'))
        results = calibrator.benchmark(AutoPyFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            self.assertEqual(result[0], "", "Incorrect backend names for case '%s' %s %s" % result)
            # similarity is not available in the autopy backend
            self.assertEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    def test_benchmark_contour(self):
        # matching all shapes will require a modification of the minArea parameter
        calibrator = Calibrator(Image('shape_blue_circle'), Image('shape_blue_circle'))
        results = calibrator.benchmark(ContourFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            self.assertTrue(result[0].endswith("+mixed"), "Incorrect backend names for case '%s' %s %s" % result)
            self.assertEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    def test_benchmark_template(self):
        calibrator = Calibrator(Image('shape_blue_circle'), Image('all_shapes'))
        results = calibrator.benchmark(TemplateFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            # only normed backends are supported
            self.assertTrue(result[0].endswith("_normed"), "Incorrect backend names for case '%s' %s %s" % result)
            self.assertEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    def test_benchmark_feature(self):
        calibrator = Calibrator(Image('n_ibs'), Image('n_ibs'))
        results = calibrator.benchmark(FeatureFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            self.assertTrue(result[0].endswith("+mixed"), "Incorrect backend names for case '%s' %s %s" % result)
            self.assertGreaterEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertLessEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    def test_benchmark_cascade(self):
        calibrator = Calibrator(Pattern('shape_blue_circle.xml'), Image('all_shapes'))
        results = calibrator.benchmark(CascadeFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            self.assertEqual(result[0], "", "Incorrect backend names for case '%s' %s %s" % result)
            # similarity is not available in the cascade backend
            self.assertEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    def test_benchmark_text(self):
        calibrator = Calibrator(Text('Text'), Image('all_shapes'))
        results = calibrator.benchmark(TextFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            self.assertTrue(result[0].startswith("mixed+"), "Incorrect backend names for case '%s' %s %s" % result)
            self.assertGreaterEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertLessEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    def test_benchmark_tempfeat(self):
        calibrator = Calibrator(Image('shape_blue_circle'), Image('all_shapes'))
        results = calibrator.benchmark(TemplateFeatureFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            # mixture of template and feature backends
            self.assertTrue("+mixed" in result[0], "Incorrect backend names for case '%s' %s %s" % result)
            self.assertTrue("_normed" in result[0], "Incorrect backend names for case '%s' %s %s" % result)
            self.assertGreaterEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertLessEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    def test_benchmark_deep(self):
        calibrator = Calibrator(Pattern('shape_blue_circle.pth'), Image('all_shapes'))
        results = calibrator.benchmark(DeepFinder())
        # pprint.pprint(results)
        self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
        for result in results:
            self.assertEqual(result[0], "", "Incorrect backend names for case '%s' %s %s" % result)
            # TODO: the needle is found but with very low similarity - possibly due to different haystack size
            #self.assertEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
            self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

if __name__ == '__main__':
    unittest.main()
