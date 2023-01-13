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
import time
import shutil
import subprocess

import common_test
from guibot.config import GlobalConfig, TemporaryConfig
from guibot.fileresolver import FileResolver
from guibot.location import Location
from guibot.region import Region
from guibot.match import Match
from guibot.target import Image, Text
from guibot.inputmap import Key
from guibot.finder import AutoPyFinder, TemplateFinder, TextFinder
from guibot.controller import PyAutoGUIController
from guibot.errors import *


class RegionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file_resolver = FileResolver()
        cls.file_resolver.add_path(os.path.join(common_test.unittest_dir, 'images'))

        cls.script_img = os.path.join(common_test.unittest_dir, 'qt5_image.py')

        # preserve values of static attributes
        cls.prev_loglevel = GlobalConfig.image_logging_level
        cls.prev_logpath = GlobalConfig.image_logging_destination
        GlobalConfig.image_logging_level = 0
        GlobalConfig.image_logging_destination = os.path.join(common_test.unittest_dir, 'tmp')

    @classmethod
    def tearDownClass(cls):
        GlobalConfig.image_logging_level = cls.prev_loglevel
        GlobalConfig.image_logging_destination = cls.prev_logpath

    def setUp(self):
        self.child_img = None
        # initialize template matching region to support multiple matches
        GlobalConfig.hybrid_match_backend = "template"
        self.region = Region()

    def tearDown(self):
        self.close_windows()
        if os.path.exists(GlobalConfig.image_logging_destination):
            shutil.rmtree(GlobalConfig.image_logging_destination)

    def assertAlmostIn(self, match, matches, delta=5):
        x, y = match
        for m in matches:
            mx, my = m
            if abs(x - mx) <= delta:
                if abs(y - my) <= delta:
                    return
        raise AssertionError("%s not near any of %s" % (match, matches))

    def show_image(self, filename):
        filename = self.file_resolver.search(filename)
        python = 'python.exe' if os.name == 'nt' else 'python3'
        self.child_img = subprocess.Popen([python, self.script_img, filename])
        # HACK: avoid small variability in loading speed
        time.sleep(3)

    def close_windows(self):
        if self.child_img is not None:
            self.child_img.terminate()
            self.wait_end(self.child_img)
            self.child_img = None

            # make sure image is really closed
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

    @unittest.skipIf(os.environ.get('DISABLE_PYAUTOGUI', "0") == "1", "PyAutoGUI disabled")
    def test_initialize(self):
        screen_width = PyAutoGUIController().width
        screen_height = PyAutoGUIController().height

        self.assertEqual(0, self.region.x)
        self.assertEqual(0, self.region.y)
        self.assertEqual(screen_width, self.region.width)
        self.assertEqual(screen_height, self.region.height)

        region = Region(10, 20, 300, 200)
        self.assertEqual(10, region.x)
        self.assertEqual(20, region.y)
        self.assertEqual(300, region.width)
        self.assertEqual(200, region.height)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_PYQT', "0") == "1",
                     "Disabled OpenCV or PyQt")
    def test_find(self):
        self.show_image('all_shapes')

        match = self.region.find(Image('shape_green_box'))
        self.assertAlmostEqual(match.x, 30, delta=5)
        self.assertAlmostEqual(match.y, 190, delta=5)
        self.assertAlmostEqual(70, match.width, delta=5)
        self.assertAlmostEqual(50, match.height, delta=5)

        # Match again - this time just pass a filename
        match = self.region.find('shape_green_box')
        self.assertAlmostEqual(match.x, 30, delta=5)
        self.assertAlmostEqual(match.y, 190, delta=5)
        self.assertAlmostEqual(70, match.width, delta=5)
        self.assertAlmostEqual(50, match.height, delta=5)

        # Test last match property
        last_match = self.region.last_match
        self.assertEqual(last_match.x, match.x)
        self.assertEqual(last_match.y, match.y)
        self.assertEqual(last_match.width, match.width)
        self.assertEqual(last_match.height, match.height)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_PYQT', "0") == "1",
                     "Disabled OpenCV or PyQt")
    def test_find_center_offset(self):
        self.show_image('all_shapes.png')

        match = self.region.find(Image('shape_blue_circle.png'))

        # Positive target offset
        match_offset = self.region.find(Image('shape_blue_circle.png').with_center_offset(200, 100))
        self.assertEqual(match.target.x + 200, match_offset.target.x)
        self.assertEqual(match.target.y + 100, match_offset.target.y)

        # Negative target offset
        match_offset = self.region.find(Image('shape_blue_circle.png').with_center_offset(-50, -30))
        self.assertEqual(match.target.x - 50, match_offset.target.x)
        self.assertEqual(match.target.y - 30, match_offset.target.y)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1",
                     "Disabled OpenCV")
    def test_find_error(self):
        try:
            self.region.find(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError as e:
            pass

        try:
            self.region.find_all(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError as e:
            pass

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_PYQT', "0") == "1",
                     "Disabled OpenCV or PyQt")
    def test_find_all(self):
        self.show_image('all_shapes')

        greenbox = Image('shape_green_box')
        matches = self.region.find_all(greenbox)
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].x, 30, delta=5)
        self.assertAlmostEqual(matches[0].y, 190, delta=5)
        self.assertAlmostEqual(70, matches[0].width, delta=5)
        self.assertAlmostEqual(50, matches[0].height, delta=5)

        redbox = Image('shape_red_box')
        matches = self.region.find_all(redbox)
        expected_matches = [(25, 25), (320, 25), (315, 115)]
        self.assertEqual(len(matches), len(expected_matches))
        for match in matches:
            self.region.hover(match)
            time.sleep(0.5)
            self.assertAlmostIn((match.x, match.y), expected_matches)
            self.assertAlmostEqual(70, match.width, delta=5)
            self.assertAlmostEqual(60, match.height, delta=5)

        pinkbox = Image('shape_pink_box')
        # pink is similar to red, so the best fuzzy matches also
        # include the three red boxes when considering color
        self.region.cv_backend.matcher.params["find"]["similarity"].value = 0.5
        self.region.cv_backend.matcher.params["template"]["nocolor"].value = False
        matches = self.region.find_all(pinkbox)
        # approximately the above coordinates since maching different needle
        expected_matches = [(25, 35), (320, 40), (320, 125), (30, 255)]
        self.assertEqual(len(matches), len(expected_matches))
        for match in matches:
            self.region.hover(match)
            time.sleep(0.5)
            self.assertAlmostIn((match.x, match.y), expected_matches)
            self.assertAlmostEqual(70, match.width, delta=5)
            self.assertAlmostEqual(50, match.height, delta=5)

        # ignore colors here so the best matches for the pink box
        # should be based on shape (the green and yellow box)
        self.region.cv_backend.matcher.params["find"]["similarity"].value = 0.8
        self.region.cv_backend.matcher.params["template"]["nocolor"].value = True
        matches = self.region.find_all(pinkbox)
        expected_matches = [(30, 120), (30, 195), (30, 255)]
        self.assertEqual(len(matches), len(expected_matches))
        for match in matches:
            self.region.hover(match)
            time.sleep(0.5)
            self.assertAlmostIn((match.x, match.y), expected_matches)
            self.assertAlmostEqual(70, match.width, delta=5)
            self.assertAlmostEqual(50, match.height, delta=5)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_PYQT', "0") == "1",
                     "Disabled OpenCV or PyQt")
    def test_find_zero_matches(self):
        self.show_image('all_shapes')

        matches = self.region.find_all(Image('shape_blue_circle'))
        self.assertEqual(len(matches), 1)
        self.close_windows()

        matches = self.region.find_all(Image('shape_blue_circle'), allow_zero=True)
        self.assertEqual(len(matches), 0)
        self.close_windows()

    def test_find_in_animation(self):
        """Test a switch where a moving match is actually matched when stopping."""
        match_frames = [Match(0, 0, 10, 20, 0, 0, 1.0), Match(30, 30, 10, 20, 0, 0, 1.0),
                        Match(30, 45, 10, 20, 0, 0, 1.0), Match(30, 45, 10, 20, 0, 0, 1.0)]
        self.region.cv_backend.find = lambda x, y: [match_frames.pop(0)]

        with TemporaryConfig() as config:
            config.wait_for_animations = True
            match = self.region.find('shape_blue_circle')
            self.assertEqual(match.x, 30)
            self.assertEqual(match.y, 45)

        self.close_windows()

    @unittest.skipIf(os.environ.get('DISABLE_PYQT', "0") == "1", "Disabled PyQt")
    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "Disabled OpenCV")
    def test_find_guess_target_image(self):
        """Test finding image from string with and without extension."""
        self.show_image('all_shapes')
        imgroot = os.path.join(common_test.unittest_dir, 'images')

        self.assertFalse(os.path.exists(os.path.join(imgroot, 'shape_blue_circle.match')))
        self.assertTrue(os.path.exists(os.path.join(imgroot, 'shape_blue_circle.png')))
        self.region.find('shape_blue_circle')
        self.region.find_all('shape_blue_circle')
        self.region.find('shape_blue_circle.png')
        self.region.find_all('shape_blue_circle.png')

    @unittest.skipIf(os.environ.get('DISABLE_PYQT', "0") == "1", "Disabled PyQt")
    @unittest.skipIf(os.environ.get('DISABLE_OCR', "0") == "1", "Disabled OCR")
    def test_find_guess_target_match(self):
        """Test target guess from match file configuration (target has match config)."""
        self.show_image('all_shapes')
        imgroot = os.path.join(common_test.unittest_dir, 'images')

        # precedence is given to match file configuration (then data file)
        self.assertTrue(os.path.exists(os.path.join(imgroot, 'mouse down.match')))
        self.assertTrue(os.path.exists(os.path.join(imgroot, 'mouse down.txt')))
        try:
            self.region.find('mouse down')
            self.fail('exception was not thrown')
        except FindError as e:
            pass
        try:
            self.region.find_all('mouse down')
            self.fail('exception was not thrown')
        except FindError as e:
            pass

    @unittest.skipIf(os.environ.get('DISABLE_PYQT', "0") == "1", "Disabled PyQt")
    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "Disabled OpenCV")
    @unittest.skipIf(os.environ.get('DISABLE_AUTOPY', "0") == "1", "Disabled AutoPy")
    def test_find_guess_target_steps(self):
        """Test target guess from data file extension (target has no match config)."""
        self.show_image('all_shapes')
        imgroot = os.path.join(common_test.unittest_dir, 'images')

        self.assertFalse(os.path.exists(os.path.join(imgroot, 'circle.match')))
        self.assertTrue(os.path.exists(os.path.join(imgroot, 'circle.steps')))
        self.region.find('circle')
        self.region.find_all('circle')

    @unittest.skipIf(os.environ.get('DISABLE_PYQT', "0") == "1", "Disabled PyQt")
    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "Disabled OpenCV")
    def test_find_guess_target_default(self):
        """Test target guess ending with default type if also unknown data type."""
        self.show_image('all_shapes')
        imgroot = os.path.join(common_test.unittest_dir, 'images')

        self.assertFalse(os.path.exists(os.path.join(imgroot, 'shape_blue_circle_unknown.match')))
        self.assertTrue(os.path.exists(os.path.join(imgroot, 'shape_blue_circle_unknown.xtx')))
        self.region.default_target_type = Image
        # NOTE: autopy cannot handle a masked image
        self.region.find('shape_blue_circle_unknown.xtx')
        self.region.find_all('shape_blue_circle_unknown.xtx')

    @unittest.skipIf(os.environ.get('DISABLE_PYQT', "0") == "1", "Disabled PyQt")
    @unittest.skipIf(os.environ.get('DISABLE_OCR', "0") == "1", "Disabled OCR")
    def test_find_guess_target_from_match(self):
        """Test target guess not failing with default text type if also missing data file."""
        self.show_image('all_shapes')
        imgroot = os.path.join(common_test.unittest_dir, 'images')

        self.assertFalse(os.path.exists(os.path.join(imgroot, 'mouse somewhere.match')))
        self.assertFalse(os.path.exists(os.path.join(imgroot, 'mouse somewhere.txt')))
        self.region.default_target_type = Text
        self.region.cv_backend = TextFinder()
        try:
            self.region.find('mouse somewhere')
            self.fail('exception was not thrown')
        except FindError as e:
            pass
        try:
            self.region.find_all('mouse somewhere')
            self.fail('exception was not thrown')
        except FindError as e:
            pass

    @unittest.skipIf(os.environ.get('DISABLE_PYQT', "0") == "1", "Disabled PyQt")
    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1", "Disabled OpenCV")
    def test_sample(self):
        """Test that sampling results in good similarity for identical visuals."""
        self.show_image('all_shapes')

        # initialize template matching region to support similarity
        shapes = Region(cv=TemplateFinder())
        similarity = shapes.sample(Image('shape_blue_circle'))
        self.assertAlmostEqual(similarity, 0.999999, delta=0.001)

        self.close_windows()

    @unittest.skipIf(os.environ.get('DISABLE_PYQT', "0") == "1", "Disabled PyQt")
    @unittest.skipIf(os.environ.get('DISABLE_AUTOPY', "0") == "1", "Disabled AutoPy")
    def test_sample_no_similarity(self):
        """Test that sampling results in 0.0 similarity if backend doesn't support it."""
        self.show_image('all_shapes')

        # autopy matching does not support similarity
        shapes = Region(cv=AutoPyFinder())
        similarity = shapes.sample(Image('shape_blue_circle'))
        self.assertEqual(similarity, 0.0)

        self.close_windows()

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_PYQT', "0") == "1",
                     "Disabled OpenCV or PyQt")
    def test_exists(self):
        self.show_image('all_shapes')

        match = self.region.find(Image('shape_blue_circle'))
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

        match = self.region.exists(Image('shape_blue_circle'))
        self.assertEqual(None, match)

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_PYQT', "0") == "1",
                     "Disabled OpenCV or PyQt")
    def test_wait(self):
        self.show_image('all_shapes')

        match = self.region.wait(Image('shape_blue_circle'), timeout=5)
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

    @unittest.skipIf(os.environ.get('DISABLE_OPENCV', "0") == "1" or
                     os.environ.get('DISABLE_PYQT', "0") == "1",
                     "Disabled OpenCV or PyQt")
    def test_wait_vanish(self):
        self.show_image('all_shapes')

        self.assertRaises(NotFindError, self.region.wait_vanish, 'all_shapes', timeout=10)

        self.close_windows()

        # assert no NotFindError is raised now
        self.assertTrue(self.region.wait_vanish('all_shapes', timeout=10))


if __name__ == '__main__':
    unittest.main()
