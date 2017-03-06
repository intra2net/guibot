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
import shutil

import common_test
from settings import GlobalSettings
from calibrator import Calibrator
from imagepath import ImagePath
from location import Location
from region import Region
from match import Match
from desktopcontrol import AutoPyDesktopControl
from image import Image
from errors import *
from imagefinder import *


class ImageFinderTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))
        GlobalSettings.image_logging_level = 0

    def tearDown(self):
        if os.path.exists(GlobalSettings.image_logging_destination):
            shutil.rmtree(GlobalSettings.image_logging_destination)

    def test_configure_backend(self):
        finder = ImageFinder()
        finder.configure_backend("feature")
        self.assertEqual(finder.params["find"]["backend"], "feature")

        finder = AutoPyMatcher()
        finder.configure()
        self.assertEqual(finder.params["find"]["backend"], "autopy")

        finder = TemplateMatcher()
        finder.configure_backend("ccoeff_normed", reset=True)
        self.assertEqual(finder.params["find"]["backend"], "template")
        self.assertEqual(finder.params["template"]["backend"], "ccoeff_normed")

        finder = FeatureMatcher()
        finder.configure()
        # test that a parameter of ORB (the current and default extractor)
        # is present in parameters while a parameter of KAZE is not present
        self.assertTrue(finder.params["fextract"].has_key("MaxFeatures"))
        self.assertFalse(finder.params["fextract"].has_key("NOctaves"))

        finder = HybridMatcher()
        finder.configure(feature_detect="ORB", feature_extract="KAZE", feature_match="BruteForce")
        self.assertEqual(finder.params["find"]["backend"], "hybrid")
        self.assertEqual(finder.params["template"]["backend"], "ccoeff_normed")
        self.assertEqual(finder.params["feature"]["backend"], "mixed")
        self.assertEqual(finder.params["fdetect"]["backend"], "ORB")
        self.assertEqual(finder.params["fextract"]["backend"], "KAZE")
        self.assertEqual(finder.params["fmatch"]["backend"], "BruteForce")

        # test that a parameter of KAZE (the new extractor) is now present
        # while the parameter of ORB is not present anymore
        self.assertTrue(finder.params["fextract"].has_key("NOctaves"))
        self.assertFalse(finder.params["fextract"].has_key("MaxFeatures"))

        # check consistency of all unchanged options
        finder.configure_backend("ccorr_normed", "template")
        self.assertEqual(finder.params["find"]["backend"], "hybrid")
        self.assertEqual(finder.params["template"]["backend"], "ccorr_normed")
        self.assertEqual(finder.params["feature"]["backend"], "mixed")
        self.assertEqual(finder.params["fdetect"]["backend"], "ORB")
        self.assertEqual(finder.params["fextract"]["backend"], "KAZE")
        self.assertEqual(finder.params["fmatch"]["backend"], "BruteForce")

        # check reset to defaults
        finder.configure(template_match="sqdiff_normed")
        self.assertEqual(finder.params["find"]["backend"], "hybrid")
        self.assertEqual(finder.params["template"]["backend"], "sqdiff_normed")
        self.assertEqual(finder.params["feature"]["backend"], "mixed")
        self.assertEqual(finder.params["fdetect"]["backend"], "ORB")
        self.assertEqual(finder.params["fextract"]["backend"], "ORB")
        self.assertEqual(finder.params["fmatch"]["backend"], "BruteForce-Hamming")

    def test_autopy_same(self):
        finder = AutoPyMatcher()
        finder.params["find"]["similarity"].value = 1.0
        matches = finder.find(Image('shape_blue_circle'), Image('all_shapes'))
        self.assertEqual(len(matches), 1)
        # AutoPy returns +1 pixel for both axes
        self.assertEqual(matches[0].x, 105)
        self.assertEqual(matches[0].y, 11)

    def test_autopy_nomatch(self):
        finder = AutoPyMatcher()
        finder.params["find"]["similarity"].value = 0.25
        matches = finder.find(Image('n_ibs'), Image('all_shapes'))
        self.assertEqual(len(matches), 0)

    def test_template_same(self):
        finder = TemplateMatcher()
        finder.params["find"]["similarity"].value = 1.0
        for template in finder.algorithms["template_matchers"]:
            # one of the backend is not perfect for this case
            if template == "sqdiff_normed":
                finder.params["find"]["similarity"].value = 0.99
            finder.configure_backend(template, "template")
            matches = finder.find(Image('shape_blue_circle'), Image('all_shapes'))
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].x, 104)
            self.assertEqual(matches[0].y, 10)

    def test_template_nomatch(self):
        finder = TemplateMatcher()
        finder.params["find"]["similarity"].value = 0.25
        for template in finder.algorithms["template_matchers"]:
            # one of the backend is too tolerant for this case
            if template == "ccorr_normed":
                continue
            finder.configure_backend(template, "template")
            matches = finder.find(Image('n_ibs'), Image('all_shapes'))
            # test template matching failure to validate needle difficulty
            self.assertEqual(len(matches), 0)

    def test_template_nocolor(self):
        finder = TemplateMatcher()
        # template matching without color is not perfect
        finder.params["find"]["similarity"].value = 0.99
        for template in finder.algorithms["template_matchers"]:
            finder.configure_backend(template, "template")
            finder.params["template"]["nocolor"].value = True
            matches = finder.find(Image('shape_blue_circle'), Image('all_shapes'))
            # test template matching failure to validate needle difficulty
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].x, 104)
            self.assertEqual(matches[0].y, 10)

    def test_feature_same(self):
        finder = FeatureMatcher()
        finder.params["find"]["similarity"].value = 1.0
        for feature in finder.algorithms["feature_projectors"]:
            for fdetect in finder.algorithms["feature_detectors"]:
                for fextract in finder.algorithms["feature_extractors"]:
                    for fmatch in finder.algorithms["feature_matchers"]:
                        finder.configure_backend(feature, "feature")
                        finder.configure(feature_detect=fdetect,
                                         feature_extract=fextract,
                                         feature_match=fmatch)
                        # also with customized synchronization to the configuration
                        finder.synchronize_backend(feature, "feature")
                        finder.synchronize(feature_detect=fdetect,
                                           feature_extract=fextract,
                                           feature_match=fmatch)
                        matches = finder.find(Image('n_ibs'), Image('n_ibs'))
                        self.assertEqual(len(matches), 1)
                        self.assertEqual(matches[0].x, 0)
                        self.assertEqual(matches[0].y, 0)

    def test_feature_nomatch(self):
        finder = FeatureMatcher()
        finder.params["find"]["similarity"].value = 0.25
        for feature in finder.algorithms["feature_projectors"]:
            for fdetect in finder.algorithms["feature_detectors"]:
                for fextract in finder.algorithms["feature_extractors"]:
                    for fmatch in finder.algorithms["feature_matchers"]:
                        finder.configure_backend(feature, "feature")
                        finder.configure(feature_detect=fdetect,
                                         feature_extract=fextract,
                                         feature_match=fmatch)
                        # also with customized synchronization to the configuration
                        finder.synchronize_backend(feature, "feature")
                        finder.synchronize(feature_detect=fdetect,
                                           feature_extract=fextract,
                                           feature_match=fmatch)
                        matches = finder.find(Image('n_ibs'), Image('all_shapes'))
                        self.assertEqual(len(matches), 0)

    def test_feature_scaling(self):
        finder = FeatureMatcher()
        finder.params["find"]["similarity"].value = 0.25
        matches = finder.find(Image('n_ibs'), Image('h_ibs_scaled'))
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 39, delta=5)
        self.assertAlmostEqual(matches[0].y, 222, delta=5)

    def test_feature_rotation(self):
        finder = FeatureMatcher()
        finder.params["find"]["similarity"].value = 0.45
        matches = finder.find(Image('n_ibs'), Image('h_ibs_rotated'))
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 435, delta=5)
        self.assertAlmostEqual(matches[0].y, 447, delta=5)

    def test_feature_viewport(self):
        finder = FeatureMatcher()
        finder.params["find"]["similarity"].value = 0.5
        matches = finder.find(Image('n_ibs'), Image('h_ibs_viewport'))
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 68, delta=5)
        self.assertAlmostEqual(matches[0].y, 18, delta=5)

    def test_feature_text_basic(self):
        needle = Image('word')
        haystack = Image('sentence_sans')
        settings = needle.match_settings

        self.match_images(haystack, needle, "feature", "sans", settings)
        # sleet to see image log better
        time.sleep(2)

    def test_feature_text_bold(self):
        needle = Image('word')
        haystack = Image('sentence_bold')
        settings = needle.match_settings

        self.match_images(haystack, needle, "feature", "bold", settings)
        # sleet to see image log better
        time.sleep(2)

    def test_feature_text_italic(self):
        needle = Image('word')
        haystack = Image('sentence_italic')
        settings = needle.match_settings

        self.match_images(haystack, needle, "feature", "italic", settings)
        # sleet to see image log better
        time.sleep(2)

    def test_feature_text_larger(self):
        needle = Image('word')
        haystack = Image('sentence_larger')
        settings = needle.match_settings

        self.match_images(haystack, needle, "feature", "larger", settings)
        # sleet to see image log better
        time.sleep(2)

    def test_feature_text_font(self):
        needle = Image('word')
        haystack = Image('sentence_font')
        settings = needle.match_settings

        self.match_images(haystack, needle, "feature", "font", settings)
        # sleet to see image log better
        time.sleep(2)

    def test_hybrid_same(self):
        finder = HybridMatcher()
        finder.params["find"]["similarity"].value = 1.0
        for hybrid in finder.algorithms["hybrid_matchers"]:
            finder.configure_backend(hybrid, "hybrid")
            matches = finder.find(Image('n_ibs'), Image('n_ibs'))
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].x, 0)
            self.assertEqual(matches[0].y, 0)

    def test_hybrid_nomatch(self):
        finder = HybridMatcher()
        finder.params["find"]["similarity"].value = 0.25
        for hybrid in finder.algorithms["hybrid_matchers"]:
            finder.configure_backend(hybrid, "hybrid")
            matches = finder.find(Image('n_ibs'), Image('all_shapes'))
            self.assertEqual(len(matches), 0)


if __name__ == '__main__':
    unittest.main()
