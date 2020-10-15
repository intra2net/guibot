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
import unittest
import pprint

import common_test
from guibot.calibrator import Calibrator
from guibot.fileresolver import FileResolver
from guibot.finder import *
from guibot.target import *
from guibot.errors import *


class CalibratorTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.patfile_resolver = FileResolver()
        self.patfile_resolver.add_path(os.path.join(common_test.unittest_dir, 'images'))

    def tearDown(self):
        if os.path.exists("pairs.list"):
            os.unlink("pairs.list")

    def calibration_setUp(self, needle, haystack, calibrate_backends):
        # use a single finder type for these tests
        finder = FeatureFinder()
        for category in calibrate_backends:
            finder.can_calibrate(category, True)
        calibrator = Calibrator(Image(needle), Image(haystack))
        return calibrator.calibrate(finder)

    def list_setUp(self):
        with open("pairs.list", "w") as f:
            f.write("n_ibs" + " " + "h_ibs_viewport" + " max" + "\n")
            f.write("n_ibs" + " " + "h_ibs_rotated" + " max" + "\n")
            f.write("n_ibs" + " " + "h_ibs_scaled" + " max" + "\n")
        return Calibrator(config="pairs.list")

    def benchmark_setUp(self):
        # remove any randomness in the unit tests in the Monte Carlo search
        CVParameter.random_value = lambda self, _mu, _sigma: self.value

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_calibrate(self):
        raw_similarity = self.calibration_setUp('n_ibs', 'n_ibs', [])
        cal_similarity = self.calibration_setUp('n_ibs', 'n_ibs',
                                                ["find", "feature", "fdetect",
                                                 "fextract", "fmatch"])
        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be less"
                             " or equal to the similarity after calibration")

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_calibrate_viewport(self):
        raw_similarity = self.calibration_setUp('n_ibs', 'h_ibs_viewport', [])
        cal_similarity = self.calibration_setUp('n_ibs', 'h_ibs_viewport',
                                                ["find", "feature", "fdetect",
                                                 "fextract", "fmatch"])
        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be less"
                             " or equal to the similarity after calibration")

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_calibrate_rotation(self):
        raw_similarity = self.calibration_setUp('n_ibs', 'h_ibs_rotated', [])
        cal_similarity = self.calibration_setUp('n_ibs', 'h_ibs_rotated',
                                                ["find", "feature", "fdetect",
                                                 "fextract", "fmatch"])
        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be less"
                             " or equal to the similarity after calibration")

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_calibrate_scaling(self):
        raw_similarity = self.calibration_setUp('n_ibs', 'h_ibs_scaled', [])
        cal_similarity = self.calibration_setUp('n_ibs', 'h_ibs_scaled',
                                                ["find", "feature", "fdetect",
                                                 "fextract", "fmatch"])
        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be less"
                             " or equal to the similarity after calibration")

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_calibrate_list(self):
        calibrator = self.list_setUp()
        # use a single finder type for these tests
        finder = FeatureFinder()
        raw_similarity = calibrator.calibrate(finder)
        for category in ["find", "feature", "fdetect", "fextract", "fmatch"]:
            finder.can_calibrate(category, True)
        cal_similarity = calibrator.calibrate(finder)
        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before calibration must be less"
                             " or equal to the similarity after calibration")

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_search(self):
        calibrator = self.list_setUp()
        # use a single finder type for these tests
        finder = FeatureFinder()
        raw_similarity = calibrator.search(finder)
        for category in ["find", "feature", "fdetect", "fextract", "fmatch"]:
            finder.can_calibrate(category, True)
        cal_similarity = calibrator.search(finder)
        self.assertLessEqual(raw_similarity, cal_similarity,
                             "Match similarity before a search must be less"
                             " or equal to the similarity after a search")

    def test_benchmark_autopy(self):
        self.benchmark_setUp()
        calibrator = Calibrator(Image('shape_blue_circle'), Image('all_shapes'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            results = calibrator.benchmark(AutoPyFinder(), calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                self.assertEqual(result[0], "", "Incorrect backend names for case '%s' %s %s" % result)
                # similarity is not available in the autopy backend
                self.assertEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_benchmark_contour(self):
        self.benchmark_setUp()
        # matching all shapes will require a modification of the minArea parameter
        calibrator = Calibrator(Image('shape_blue_circle'), Image('shape_blue_circle'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            results = calibrator.benchmark(ContourFinder(), calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                self.assertIn("mixed", result[0], "Incorrect backend names for case '%s' %s %s" % result)
                self.assertEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_benchmark_template(self):
        self.benchmark_setUp()
        calibrator = Calibrator(Image('shape_blue_circle'), Image('all_shapes'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            results = calibrator.benchmark(TemplateFinder(), calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                # only normed backends are supported
                self.assertIn("_normed", result[0], "Incorrect backend names for case '%s' %s %s" % result)
                self.assertEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    @unittest.skip("Unit test takes too long")
    #@unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_benchmark_feature(self):
        self.benchmark_setUp()
        calibrator = Calibrator(Image('n_ibs'), Image('n_ibs'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            results = calibrator.benchmark(FeatureFinder(), calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                self.assertIn("mixed", result[0], "Incorrect backend names for case '%s' %s %s" % result)
                self.assertGreaterEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertLessEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_benchmark_cascade(self):
        self.benchmark_setUp()
        calibrator = Calibrator(Pattern('shape_blue_circle.xml'), Image('all_shapes'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            results = calibrator.benchmark(CascadeFinder(), calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                self.assertEqual(result[0], "", "Incorrect backend names for case '%s' %s %s" % result)
                # similarity is not available in the cascade backend
                self.assertEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_OCR', "0") == "1",
                     "Disabled OpenCV or OCR")
    def test_benchmark_text(self):
        self.benchmark_setUp()
        calibrator = Calibrator(Text('Text'), Image('all_shapes'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            finder = TextFinder()
            # the text backend has too many benchmarking combinations so let's restrict here
            finder.algorithms["threshold_filters2"] = ("adaptive",)
            finder.algorithms["threshold_filters3"] = ("adaptive",)
            finder.algorithms["threshold_filters2"] = ("adaptive",)
            finder.algorithms["threshold_filters3"] = ("adaptive",)
            # also get rid of these since they are not implemented anyway
            finder.algorithms["text_detectors"] = list(finder.algorithms["text_detectors"])
            finder.algorithms["text_detectors"].remove("components")
            import cv2
            # TODO: deprecate OpenCV 3.X versions after time
            if cv2.__version__.startswith("3."):
                finder.algorithms["text_detectors"].remove("east")
            finder.algorithms["text_recognizers"] = list(finder.algorithms["text_recognizers"])
            finder.algorithms["text_recognizers"].remove("beamSearch")
            # one tesseract backend is enough for the unit test
            finder.algorithms["text_recognizers"].remove("tesseract")
            finder.algorithms["text_recognizers"].remove("pytesseract")
            results = calibrator.benchmark(finder, calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                self.assertIn("mixed", result[0], "Incorrect backend names for case '%s' %s %s" % result)
                self.assertGreaterEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertLessEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    @unittest.skip("Unit test takes too long")
    #@unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "OpenCV disabled")
    def test_benchmark_tempfeat(self):
        self.benchmark_setUp()
        calibrator = Calibrator(Image('shape_blue_circle'), Image('all_shapes'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            results = calibrator.benchmark(TemplateFeatureFinder(), calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                # mixture of template and feature backends
                self.assertIn("mixed", result[0], "Incorrect backend names for case '%s' %s %s" % result)
                self.assertIn("_normed", result[0], "Incorrect backend names for case '%s' %s %s" % result)
                self.assertGreaterEqual(result[1], 0.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertLessEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

    @unittest.skipIf(os.environ.get('DISABLE_PYTORCH', "0") == "1", "PyTorch disabled")
    def test_benchmark_deep(self):
        self.benchmark_setUp()
        calibrator = Calibrator(Pattern('cat'), Image('coco_cat'))
        for calibration, random_starts in [(False, 0), (False, 1), (True, 0), (True, 1)]:
            finder = DeepFinder()
            # get rid of backends that are not implemented anyway
            finder.algorithms["deep_learners"] = list(finder.algorithms["deep_learners"])
            finder.algorithms["deep_learners"].remove("tensorflow")
            results = calibrator.benchmark(finder, calibration=calibration, random_starts=random_starts)
            # pprint.pprint(results)
            self.assertGreater(len(results), 0, "There should be at least one benchmarked method")
            for result in results:
                self.assertEqual("pytorch", result[0], "Incorrect backend names for case '%s' %s %s" % result)
                # TODO: the needle is found but with very low similarity - possibly due to different haystack size
                #self.assertEqual(result[1], 1.0, "Incorrect similarity for case '%s' %s %s" % result)
                self.assertGreater(result[2], 0.0, "Strictly positive time is required to run case '%s' %s %s" % result)

if __name__ == '__main__':
    unittest.main()
