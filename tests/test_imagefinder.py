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

import cv, cv2
from tempfile import NamedTemporaryFile

from imagefinder import ImageFinder
from imagepath import ImagePath
from location import Location
from region import Region
from match import Match
from desktopcontrol import DesktopControl
from image import Image
from errors import *

class ImageTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))
        self.imagepath.add_path(os.path.join(common_test.examples_dir, 'images'))
        self.imagepath.add_path(".")

        self.script_show_picture = os.path.join(common_test.unittest_dir, 'show_picture.py')

    def setUp(self):
        self.shown_pictures = []

    def tearDown(self):
        self.close_windows()
        needle_file = os.path.join(common_test.unittest_dir, 'images/', 'needle.png')
        try:
            os.unlink(needle_file)
        except OSError:
            pass

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

    def show_image(self, filename, title = "show_image"):
        filename = self.imagepath.search(filename)
        self.shown_pictures.append(subprocess.Popen(['python',
                                                    self.script_show_picture,
                                                    filename, title]))

    def close_windows(self):
        time.sleep(2)
        for window in self.shown_pictures:
            window.terminate()
            self.wait_end(window)

            # Hack to make sure app is really closed
            time.sleep(0.5)

        self.shown_pictures = []

    def draw_needle_features(self, needle, haystack):
        finder = ImageFinder()
        finder.image_logging = True
        self.algorithms = (finder.detect_features, finder.extract_features, finder.match_features)

        # use private methods for unit testing to visualize internal structure
        _, opencv_needle = finder._get_opencv_images(haystack, needle)
        hkp, hdc, nkp, ndc = finder._detect_features(haystack, needle,
                                                     detect = self.algorithms[0],
                                                     extract = self.algorithms[1])
        mhkp, hkp, mnkp, nkp = finder._match_features(hkp, hdc, nkp, ndc,
                                                      0.0, match = self.algorithms[2])
        #print "matched %s\\%s in haystack with %s\\%s in needle" % (len(mhkp), len(hkp),
        #                                                            len(mnkp), len(nkp))
        self.assertEqual(len(mhkp), len(mnkp), "The matched keypoints in the haystack and "\
                        "the image should be equal.")
        # this rule does not apply to the haystack since it may be scaled and reduced in size
        self.assertGreaterEqual(len(nkp), len(mnkp), "The matched keypoints in the needle "\
                                "should be fewer than all detected keypoints in the needle")
        self.assertGreaterEqual(len(mhkp), 4, "Minimum of 4 keypoints should be matched in "\
                                "the haystack while %s were matched" % len(mhkp))
        self.assertGreaterEqual(len(mnkp), 4, "Minimum of 4 keypoints should be matched in "\
                                "the needle while %s were matched" % len(mnkp))

        # draw focus point as well as matched and unmatched features
        for kp in nkp:
            if kp in mnkp:
                color = (0, 255, 0)
            else:
                color = (0, 0, 255)
            x,y = kp.pt
            cv2.circle(opencv_needle, (int(x),int(y)), 2, color, -1)
        (ocx, ocy) = (needle.get_width() / 2, needle.get_height() / 2)
        cv2.circle(opencv_needle, (int(ocx),int(ocy)), 4, (255,0,0), -1)

        needle_file = os.path.join(common_test.unittest_dir, 'images/', 'needle.png')
        cv2.imwrite(needle_file, opencv_needle)
        self.show_image(needle_file, "needle")

        # if these functions are fixed in the future, they could simplify the
        # code since the drawn image can directly be shown and saved only if
        # needed (while imshow works here, destroyAllWindows fails)
        #cv2.imshow("needle", opencv_needle)
        #cv2.waitKey(5000)
        #cv2.destroyAllWindows()

    def draw_haystack_hotmap(self, haystack, needle, title, logging = 20):
        finder = ImageFinder()
        finder.image_logging = True
        match = finder.find_features(haystack, needle, 0.0)
        self.assertIsNotNone(match, "The original needle image "\
                             "should be matched in the screen.")
        hotmap_file = os.path.join('last_hotmap.png')
        self.show_image(hotmap_file, title)


    def test_find_feature_basic_viewport(self):
        needle = Image('n_ibs')
        haystack = Image('h_ibs_viewport')
        self.draw_needle_features(needle, haystack)
        self.draw_haystack_hotmap(haystack, needle,
                                  "basic viewport", 10)

    def test_find_feature_rotation(self):
        needle = Image('n_ibs')
        haystack = Image('h_ibs_rotated')
        self.draw_needle_features(needle, haystack)
        self.draw_haystack_hotmap(haystack, needle,
                                  "rotated + viewport", 10)

    def test_find_feature_scaling(self):
        needle = Image('n_ibs')
        haystack = Image('h_ibs_scaled')
        self.draw_needle_features(needle, haystack)
        self.draw_haystack_hotmap(haystack, needle,
                                  "scaled + viewport", 10)

    def test_viewport_template_match(self):
        needle = Image('n_ibs')
        self.show_image('h_ibs_viewport')
        time.sleep(3)
        haystack = DesktopControl().capture_screen()

        # test template matching failure to validate needle difficulty
        match = ImageFinder().find_image(haystack, needle, 0.9, 0, 0,
                                     haystack.width, haystack.height,
                                     nocolor = True)
        self.assertIsNone(match, "Template matching should fail finding "\
                          "viewport transformed image.")

    def test_viewport_in_screen(self):
        needle = Image('n_ibs')
        self.show_image('h_ibs_viewport')
        time.sleep(3)
        haystack = DesktopControl().capture_screen()

        self.draw_needle_features(needle, haystack)
        self.draw_haystack_hotmap(haystack, needle,
                                  "screen + viewport", 10)

    def test_viewport_mouse_hover(self):
        needle = Image('n_ibs')
        self.show_image('h_ibs_viewport')
        time.sleep(3)
        haystack = DesktopControl().capture_screen()

        # test hovering over viewport needle
        match = ImageFinder().find_features(haystack, needle, 0.0)
        self.assertIsNotNone(match, "The viewport transformed image "\
                             "should be matched in the screen.")
        Region().hover(match)

    def test_benchmark_find(self):
        haystack = Image('all_shapes')
        needle = Image('shape_blue_circle')

        finder = ImageFinder()
        results = finder.benchmark_find(haystack, needle)
        #print results
        self.assertGreater(len(results), 0, "The benchmarked methods "\
                           "should be more than one for the blue circle")

    def test_find_feature_text_shapes(self):
        needle = Image('shape_text')
        haystack = Image('all_shapes')
        self.draw_needle_features(needle, haystack)
        self.draw_haystack_hotmap(haystack, needle, "shape text")

if __name__ == '__main__':
    unittest.main()

