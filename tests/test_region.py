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

from imagepath import ImagePath
from location import Location
from region import Region
from match import Match
from desktopcontrol import DesktopControl
from image import Image
from key import Key
from errors import *

class RegionTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))
        self.imagepath.add_path(os.path.join(common_test.examples_dir, 'images'))

        self.script_show_picture = os.path.join(common_test.unittest_dir, 'show_picture.py')
        self.script_qt4_guitest = os.path.join(common_test.unittest_dir, 'qt4_guitest.py')

    def setUp(self):
        self.child_show_picture = None

    def tearDown(self):
        self.close_windows()

    def test_basic(self):
        screen_width = DesktopControl().get_width()
        screen_height = DesktopControl().get_height()

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

    def show_image(self, filename):
        filename = self.imagepath.search(filename)

        self.child_show_picture = subprocess.Popen(['python', self.script_show_picture, filename])

    def close_windows(self):
        if self.child_show_picture is not None:
            self.child_show_picture.terminate()
            self.wait_end(self.child_show_picture)
            self.child_show_picture = None

            # Hack to make sure app is really closed
            time.sleep(0.5)

    def test_configure_find(self):
        region = Region()
        region.configure_find(find_image = "feature")
        self.assertEqual(region.imagefinder.eq.get_backend("find"), "feature")

        region.configure_find(find_image = "template", template_match = "autopy")
        self.assertEqual(region.imagefinder.eq.get_backend("find"), "template")
        self.assertEqual(region.imagefinder.eq.get_backend("tmatch"), "autopy")

        # test that a parameter of BRIEF (the current and default extractor)
        # is present in parameters while a parameter of FREAK is not present
        self.assertTrue(region.imagefinder.eq.p["fextract"].has_key("bytes"))
        self.assertFalse(region.imagefinder.eq.p["fextract"].has_key("nbOctave"))

        region.configure_find(find_image = "feature", feature_detect = "ORB",
                              feature_extract = "FREAK", feature_match = "BruteForce")
        self.assertEqual(region.imagefinder.eq.get_backend("find"), "feature")
        self.assertEqual(region.imagefinder.eq.get_backend("fdetect"), "ORB")
        self.assertEqual(region.imagefinder.eq.get_backend("fextract"), "FREAK")
        self.assertEqual(region.imagefinder.eq.get_backend("fmatch"), "BruteForce")

        # test that a parameter of FREAK (the new extractor) is now present
        # while the parameter of BRIEF is not present anymore
        self.assertTrue(region.imagefinder.eq.p["fextract"].has_key("nbOctave"))
        self.assertTrue(region.imagefinder.eq.p["fextract"].has_key("nbOctave"))

        # check consistency of all unchanged options
        region.configure_find(find_image = None, template_match = "ccorr_normed")
        self.assertEqual(region.imagefinder.eq.get_backend("find"), "feature")
        self.assertEqual(region.imagefinder.eq.get_backend("tmatch"), "ccorr_normed")
        self.assertEqual(region.imagefinder.eq.get_backend("fdetect"), "ORB")
        self.assertEqual(region.imagefinder.eq.get_backend("fextract"), "FREAK")
        self.assertEqual(region.imagefinder.eq.get_backend("fmatch"), "BruteForce")

    def test_find(self):
        self.show_image('all_shapes')

        region = Region()
        match = region.find(Image('shape_blue_circle'))

        self.assertEqual(165, match.get_width())
        self.assertEqual(151, match.get_height())

        # Match again - this time just pass a filename
        match = region.find('shape_pink_box')
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

        match = Region().find(Image('shape_blue_circle.png'))

        # Positive target offset
        match_offset = Region().find(Image('shape_blue_circle.png').target_offset(200, 100))
        self.assertEqual(match.get_target().get_x() + 200, match_offset.get_target().get_x())
        self.assertEqual(match.get_target().get_y() + 100, match_offset.get_target().get_y())

        # Positive target offset
        match_offset = Region().find(Image('shape_blue_circle.png').target_offset(-50, -30))
        self.assertEqual(match.get_target().get_x() - 50, match_offset.get_target().get_x())
        self.assertEqual(match.get_target().get_y() - 30, match_offset.get_target().get_y())

    def test_find_error(self):
        try:
            Region().find(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

        try:
            Region().find_all(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

    def test_zero_matches(self):
        self.show_image('all_shapes')

        matches = Region().find_all(Image('shape_blue_circle'))
        self.assertEqual(len(matches), 1)

        self.close_windows()

        matches = Region().find_all(Image('shape_blue_circle'), allow_zero = True)
        self.assertEqual(len(matches), 0)

        self.close_windows()

    def test_find_all(self):
        self.show_image('all_shapes')
        region = Region()
        # TODO: find should consider both autopy
        # and OpenCV but both may not be supported
        # at developer's platform
        #region.imagefinder = ImageFinder()

        matches = region.find_all('shape_green_box')
        self.assertEqual(len(matches), 1)
        self.assertEqual(67, matches[0].get_width())
        self.assertEqual(52, matches[0].get_height())

        matches = region.find_all('shape_red_box')
        self.assertEqual(len(matches), 3)
        for match in matches:
            region.hover(match)
            time.sleep(0.5)
            self.assertEqual(68, match.get_width())
            self.assertEqual(56, match.get_height())

        # pink is similar to red, so the best fuzzy matches are
        # the three red boxes when considering color
        region.imagefinder.eq.p["find"]["similarity"].value = 0.5
        matches = region.find_all('shape_pink_box')
        self.assertEqual(len(matches), 4)
        for match in matches:
            region.hover(match)
            time.sleep(0.5)
            self.assertEqual(69, match.get_width())
            self.assertEqual(48, match.get_height())

        # ignore colors here so the best matches for the pink box
        # should be based on shape (the green and yellow box)
        region.imagefinder.eq.p["find"]["similarity"].value = 0.8
        region.imagefinder.eq.p["find"]["nocolor"].value = True
        matches = region.find_all('shape_pink_box')
        self.assertEqual(len(matches), 3)
        for match in matches:
            region.hover(match)
            time.sleep(0.5)
            self.assertEqual(69, match.get_width())
            self.assertEqual(48, match.get_height())

    def test_exists(self):
        self.show_image('all_shapes')

        match = Region().find(Image('shape_blue_circle'))
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

        match = Region().exists(Image('shape_blue_circle'))
        self.assertEqual(None, match)

        # TODO: it is not clear what the following two lines do
        # since windows should already be closed?
        self.close_windows()

        self.assertTrue(Region().wait_vanish('all_shapes'))

    def test_wait(self):
        self.show_image('all_shapes')
        match = Region().wait(Image('shape_blue_circle'), timeout = 5)
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

    def test_wait_vanish(self):
        self.show_image('all_shapes')
        time.sleep(3)
        self.assertFalse(Region().wait_vanish('all_shapes', timeout = 5))

        self.close_windows()
        self.assertTrue(Region().wait_vanish('all_shapes', timeout = 10))

    def test_hover(self):
        # Hover over Location
        self.show_image('all_shapes')
        region = Region()
        match = region.find(Image('shape_blue_circle'))
        match.hover(match.get_target())

        # Hover over Image with 50% similarity
        region.imagefinder.eq.p["find"]["similarity"].value = 0.5
        region.hover(Image('shape_pink_box'))

        self.close_windows()

        # Test hovering over projected location
        self.show_image('h_ibs_viewport')
        time.sleep(2)
        # TODO: currently the match similarity is very low although
        # the image if matched properly - need to find a way to increase
        # the similarity while preserving the robustness of the feature matching
        region.configure_find(find_image = "feature")
        region.imagefinder.eq.p["find"]["similarity"].value = 0.1
        match = region.find(Image('n_ibs'))
        Region().hover(match.get_target())

    def test_click(self):
        # TODO: accept method
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS with 0.8
        region.configure_find(find_image = "hybrid")
        region.imagefinder.eq.p["fdetect"]["nzoom"].value = 4.0
        region.imagefinder.eq.p["fdetect"]["hzoom"].value = 4.0

        # method 2: SUCCESS with 0.5
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.5
        # or: Image('qt4gui_button').similarity(0.5)

        region.click('qt4gui_button')
        region.wait_vanish('qt4gui_button')

        self.assertEqual(0, self.wait_end(child_pipe))

    def test_double_click(self):
        # TODO: accept method
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS with 0.8
        region.configure_find(find_image = "hybrid")
        region.imagefinder.eq.p["fdetect"]["nzoom"].value = 4.0
        region.imagefinder.eq.p["fdetect"]["hzoom"].value = 4.0

        # method 2: FAIL
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.4

        region.double_click('qt4gui_double_click')

        self.assertEqual(0, self.wait_end(child_pipe))

    def test_right_click(self):
        # TODO: reduce solution
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS with 0.8
        cm_label = Image('qt4gui_contextmenu_label')
        cm_label.use_own_settings = True
        cm_label.match_settings.configure_backend(find_image = "hybrid")
        cm_label.match_settings.p["find"]["front_similarity"].value = 0.5
        cm_label.match_settings.p["find"]["nocolor"].value = True
        #cm_label.match_settings.p["fdetect"]["nFeatures"].value = 4000
        cm_label.match_settings.p["fdetect"]["nzoom"].value = 4.0
        cm_label.match_settings.p["fdetect"]["hzoom"].value = 4.0

        cm_quit = Image('qt4gui_contextmenu_quit')
        cm_quit.use_own_settings = True
        cm_quit.match_settings.configure_backend(find_image = "hybrid")
        cm_quit.match_settings.p["find"]["front_similarity"].value = 0.55
        cm_quit.match_settings.p["find"]["similarity"].value = 0.9
        cm_quit.match_settings.p["find"]["nocolor"].value = True
        cm_quit.match_settings.p["fdetect"]["nFeatures"].value = 5000
        cm_quit.match_settings.p["fdetect"]["nzoom"].value = 4.0
        cm_quit.match_settings.p["fdetect"]["hzoom"].value = 4.0
        cm_quit.match_settings.p["find"]["ransacReprojThreshold"].value = 5.0
        #cm_quit.match_settings.p["fmatch"]["ratioTest"].value = True
        #cm_quit.match_settings.p["fmatch"]["symmetryTest"].value = True

        # method 2: FAIL on Quit with 0.5
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.5

        region.right_click(cm_label).nearby(200).idle(3).click(cm_quit)

        self.assertEqual(0, self.wait_end(child_pipe))

    def test_press(self):
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])
        time.sleep(1)
        Region().press(Key.ESC)
        self.assertEqual(0, self.wait_end(child_pipe))

        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])
        time.sleep(1)
        Region().press([Key.ALT, Key.F4])
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_press_at(self):
        # TODO: accept method
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS with 0.8
        region.configure_find(find_image = "hybrid")
        region.imagefinder.eq.p["fdetect"]["nzoom"].value = 4.0
        region.imagefinder.eq.p["fdetect"]["hzoom"].value = 4.0

        # method 2: FAIL
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.5

        region.press_at('qt4gui_lineedit2', keys=[Key.ENTER])

        Region().wait_vanish('qt4gui_lineedit2')
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_type_text(self):
        # TODO: accept method
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS with 0.8
        region.configure_find(find_image = "hybrid")
        region.imagefinder.eq.p["fdetect"]["nzoom"].value = 4.0
        region.imagefinder.eq.p["fdetect"]["hzoom"].value = 4.0

        # method 2: SUCCESS with 0.5
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.5

        region.click('qt4gui_lineedit')
        time.sleep(0.2)
        Region().type_text('quit')

        # TODO: solve this and all wait vanish or remove them since they
        # don't test anything
        Region().wait_vanish('qt4gui_lineedit')
        #Region().wait_vanish(Image('qt4gui_lineedit').similarity(0.5))
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_type_at(self):
        # TODO: accept method
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS with 0.8
        region.configure_find(find_image = "hybrid")
        region.imagefinder.eq.p["fdetect"]["nzoom"].value = 4.0
        region.imagefinder.eq.p["fdetect"]["hzoom"].value = 4.0

        # method 2: SUCCESS with 0.5
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.5

        region.type_at('qt4gui_lineedit', text='quit')

        Region().wait_vanish('qt4gui_lineedit')
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_drag_drop(self):
        # TODO: reduce solution
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS
        drag_text = Image('qt4gui_textedit')
        drag_text.use_own_settings = True
        drag_text.match_settings.configure_backend(find_image = "hybrid")
        drag_text.match_settings.p["find"]["front_similarity"].value = 0.4
        drag_text.match_settings.p["find"]["similarity"].value = 0.7
        drag_text.match_settings.p["fdetect"]["nzoom"].value = 4.0
        drag_text.match_settings.p["fdetect"]["hzoom"].value = 10.0

        drop_text = Image('qt4gui_lineedit')
        drop_text.use_own_settings = True
        drop_text.match_settings.configure_backend(find_image = "hybrid")
        drop_text.match_settings.p["fdetect"]["nzoom"].value = 4.0
        drop_text.match_settings.p["fdetect"]["hzoom"].value = 4.0

        # method 2: FAIL
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.5

        region.drag_drop(drag_text, drop_text)

        Region().wait_vanish('qt4gui_textedit')
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_drag(self):
        # TODO: reduce solution
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        # method 1: SUCCESS
        drag_text = Image('qt4gui_textedit')
        drag_text.use_own_settings = True
        drag_text.match_settings.configure_backend(find_image = "hybrid")
        drag_text.match_settings.p["find"]["front_similarity"].value = 0.4
        drag_text.match_settings.p["find"]["similarity"].value = 0.7
        drag_text.match_settings.p["fdetect"]["nzoom"].value = 4.0
        drag_text.match_settings.p["fdetect"]["hzoom"].value = 10.0

        Region().drag(drag_text)

        drag_hover = Image('qt4gui_label1')
        drag_hover.use_own_settings = True
        drag_hover.match_settings.configure_backend(find_image = "hybrid")
        drag_hover.match_settings.p["find"]["front_similarity"].value = 0.4
        drag_hover.match_settings.p["find"]["similarity"].value = 0.9
        drag_hover.match_settings.p["find"]["ransacReprojThreshold"].value = 3.0
        drag_hover.match_settings.p["fdetect"]["nzoom"].value = 4.0
        drag_hover.match_settings.p["fdetect"]["hzoom"].value = 4.0

        Region().hover(drag_hover)

        # toggled buttons cleanup
        Region().desktop.mouse_up()

        Region().wait_vanish('qt4gui_label1')
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_drop_at(self):
        # TODO: solve
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        drag_text = Image('qt4gui_textedit')
        drag_text.use_own_settings = True
        drag_text.match_settings.configure_backend(find_image = "hybrid")
        drag_text.match_settings.p["find"]["front_similarity"].value = 0.4
        drag_text.match_settings.p["find"]["similarity"].value = 0.7
        drag_text.match_settings.p["fdetect"]["nzoom"].value = 4.0
        drag_text.match_settings.p["fdetect"]["hzoom"].value = 10.0

        Region().drag(drag_text)

        hover_drop = Image('qt4gui_label2')
        hover_drop.use_own_settings = True
        hover_drop.match_settings.configure_backend(find_image = "hybrid")
        hover_drop.match_settings.p["find"]["front_similarity"].value = 0.4
        hover_drop.match_settings.p["find"]["similarity"].value = 0.8
        hover_drop.match_settings.p["find"]["ransacReprojThreshold"].value = 3.0
        hover_drop.match_settings.p["fdetect"]["nzoom"].value = 4.0
        hover_drop.match_settings.p["fdetect"]["hzoom"].value = 4.0

        Region().hover(hover_drop)
        self.assertFalse(Region().wait_vanish(hover_drop, timeout=3))

        Region().drop_at(hover_drop)

        Region().wait_vanish('qt4gui_label2')
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_mouse_down(self):
        # TODO: reduce solution
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: SUCCESS with 0.9
        region.configure_find(find_image = "hybrid")
        region.imagefinder.eq.p["find"]["front_similarity"].value = 0.4
        region.imagefinder.eq.p["find"]["similarity"].value = 0.9
        region.imagefinder.eq.p["find"]["ransacReprojThreshold"].value = 3.0
        region.imagefinder.eq.p["fdetect"]["nzoom"].value = 4.0
        region.imagefinder.eq.p["fdetect"]["hzoom"].value = 4.0

        # method 2: FAIL (on cleaner background with 0.4)
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.4

        region.idle(2).mouse_down(Image('qt4gui_label3'))

        # toggled buttons cleanup
        Region().desktop.mouse_up()

        Region().wait_vanish('qt4gui_label3')
        self.assertEqual(0, self.wait_end(child_pipe))

    def test_mouse_up(self):
        # TODO: reduce solution
        child_pipe = subprocess.Popen(['python', self.script_qt4_guitest])

        region = Region()

        # method 1: FAIL (on cleaner background with 0.8)
        region.configure_find(find_image = "hybrid")
        # need to be less selective at template matching due to its lack of accuracy
        region.imagefinder.eq.p["find"]["front_similarity"].value = 0.5
        # need to be very selective to exclude very similar text
        region.imagefinder.eq.p["find"]["similarity"].value = 0.9
        #region.imagefinder.eq.p["find"]["ransacReprojThreshold"].value = 3.0
        region.imagefinder.eq.p["fdetect"]["nzoom"].value = 4.0
        region.imagefinder.eq.p["fdetect"]["hzoom"].value = 4.0

        # method 2: FAIL (on cleaner background with 0.5)
        #region.imagefinder.eq.p["find"]["similarity"].value = 0.5

        region.idle(2).mouse_down('qt4gui_label4')

        # cannot use label 4 since the cursor is already on top of it
        self.assertFalse(region.wait_vanish('qt4gui_label4', timeout=3))
        region.mouse_up('qt4gui_label4')
        self.assertTrue(region.wait_vanish('qt4gui_label4', timeout=5))

        self.assertEqual(0, self.wait_end(child_pipe))

    def test_get_mouse_location(self):
        Region().hover(Location(0,0))

        pos = Region().get_mouse_location()
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.get_x() < 5)
        self.assertTrue(pos.get_y() < 5)

        Region().hover(Location(30,20))

        pos = Region().get_mouse_location()
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.get_x() > 25 and pos.get_x() < 35)
        self.assertTrue(pos.get_y() > 15 and pos.get_y() < 25)


if __name__ == '__main__':
    unittest.main()
