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

        self.script_show_picture = os.path.join(common_test.unittest_dir, 'show_picture.py')

    def setUp(self):
        self.child_show_picture = None

    def tearDown(self):
        self.close_windows()

    def show_image(self, filename):
        filename = self.imagepath.search(filename)

        self.child_show_picture = subprocess.Popen(['python', self.script_show_picture, filename])

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

    def close_windows(self):
        if self.child_show_picture is not None:
            self.child_show_picture.terminate()
            self.wait_end(self.child_show_picture)
            self.child_show_picture = None

            # Hack to make sure app is really closed
            time.sleep(0.5)

    def draw_features_and_clicking_point(self, needle, haystack, extra_title):
        finder = ImageFinder()
        self.algorithms = (finder.detect_features, finder.extract_features, finder.match_features)
        (ocx, ocy) = (needle.get_width() / 2, needle.get_height() / 2)

        # use private methods for unit testing to visualize internal structure
        opencv_haystack, opencv_needle = finder._get_opencv_images(haystack, needle)
        hkp, hdc, nkp, ndc = finder._detect_features(haystack, needle,
                                                     detect = self.algorithms[0],
                                                     extract = self.algorithms[1])
        mhkp, hkp, mnkp, nkp = finder._match_features(hkp, hdc, nkp, ndc,
                                                      0.0, match = self.algorithms[2])
        print "matched %s\\%s from haystack with %s\\%s from needle" % (len(mhkp), len(hkp),
                                                                        len(mnkp), len(nkp))
        pos = finder.find_features(haystack, needle, 0.0)
        if pos == None:
            raise FindError
        mcx, mcy = pos.xpos, pos.ypos

        # draw projected image center as well as matched and unmatched features
        cv2.circle(opencv_haystack, (int(mcx),int(mcy)), 2,(0,255,0),-1)
        cv2.circle(opencv_needle, (int(ocx),int(ocy)), 2,(0,255,0),-1)
        for kp in hkp:
            if kp in mhkp:
                # draw matched keypoints in red color
                color = (0, 0, 255)
            else:
                # draw unmatched in blue color
                color = (255, 0, 0)
            # draw matched key points on original h image
            x,y = kp.pt
            cv2.circle(opencv_haystack, (int(x),int(y)), 2, color, -1)
        for kp in nkp:
            if kp in mnkp:
                # draw matched keypoints in red color
                color = (0, 0, 255)
            else:
                # draw unmatched in blue color
                color = (255, 0, 0)
            # draw matched key points on original n image
            x,y = kp.pt
            cv2.circle(opencv_needle, (int(x),int(y)), 2, color, -1)
        cv2.imshow('haystack' + extra_title, opencv_haystack)
        cv2.imshow('needle', opencv_needle)
        cv2.waitKey(5000)
        # TODO: this function does not work and contaminates the tests
        # this should be resolved with the improved image finder debugging
        # which would only use our showimage function and some more
        cv2.destroyAllWindows()

    def find_feature_basic_viewport(self):
        needle = Image('n_ibs')
        haystack = Image('h_ibs_viewport')
        self.draw_features_and_clicking_point(needle, haystack, " viewport")

    def test_find_feature_rotation(self):
        needle = Image('n_ibs')
        haystack = Image('h_ibs_rotated')
        self.draw_features_and_clicking_point(needle, haystack, " rotation")

    def test_find_feature_scaling(self):
        needle = Image('n_ibs')
        haystack = Image('h_ibs_scaled')
        self.draw_features_and_clicking_point(needle, haystack, " scaling")

    def test_viewport_template_match(self):
        desktop = DesktopControl()
        needle = Image('n_ibs')
        needle_viewport = Image('h_ibs_viewport')
        self.show_image('h_ibs_viewport')
        time.sleep(3)
        haystack = desktop.capture_screen()

        # test template matching failure to validate needle difficulty
        match = ImageFinder().find_image(haystack, needle, 0.9, 0, 0,
                                     haystack.width, haystack.height,
                                     nocolor = True)
        self.assertEqual(match, None)

    def test_viewport_in_screen(self):
        desktop = DesktopControl()
        needle = Image('n_ibs')
        needle_viewport = Image('h_ibs_viewport')
        self.show_image('h_ibs_viewport')
        time.sleep(3)
        haystack = desktop.capture_screen()

        # visualize matched features before hover test
        self.draw_features_and_clicking_point(needle, haystack, " screen")

    def test_viewport_hover(self):
        desktop = DesktopControl()
        needle = Image('n_ibs')
        needle_viewport = Image('h_ibs_viewport')
        self.show_image('h_ibs_viewport')
        time.sleep(3)
        haystack = desktop.capture_screen()

        # test hovering over viewport needle
        match = ImageFinder().find_features(haystack, needle, 0.0)
        if match is not None:
            #match = Match(match.get_x(), match.get_y(), needle)
            Region().hover(match)
        else:
            raise FindError

if __name__ == '__main__':
    unittest.main()

