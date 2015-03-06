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
import re
import unittest
import shutil
import logging

import cv
import cv2
from tempfile import NamedTemporaryFile

import common_test
from settings import Settings
from imagefinder import ImageFinder
from imagelogger import ImageLogger
from imagepath import ImagePath
from image import Image
from errors import *


class ImageLoggerTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.logpath = os.path.join(common_test.unittest_dir, 'tmp')
        Settings.image_logging_level(0)
        Settings.image_logging_destination(self.logpath)
        Settings.image_logging_step_width(4)

        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))

    def setUp(self):
        os.mkdir(self.logpath)
        ImageLogger.step = 1

    def tearDown(self):
        shutil.rmtree(self.logpath)

    @classmethod
    def tearDownClass(self):
        Settings.image_logging_level(logging.ERROR)
        Settings.image_logging_destination(".")
        Settings.image_logging_step_width(3)

    def _get_matches_in(self, pattern, list):
        return [match.group(0) for el in list for match in [re.search(pattern, el)] if match]

    def _test_simple_match(self, backend):
        if backend == "template":
            needle_name = 'shape_blue_circle'
            haystack_name = 'all_shapes'
        elif backend == "feature":
            needle_name = 'n_ibs'
            haystack_name = 'h_ibs_viewport'

        needle = Image(needle_name)
        haystack = Image(haystack_name)
        needle.use_own_settings = True
        settings = needle.match_settings
        settings.configure_backend(find_image=backend)

        finder = ImageFinder()
        finder.find(needle, haystack)

        dump_files = os.listdir(self.logpath)
        self.assertEquals(len(dump_files), 4, "There must be a total of 4 different dumped files in %s" % dump_files)

        step_files = self._get_matches_in('imglog\d\d\d\d-.+\.png', dump_files)
        first_step_files = self._get_matches_in('imglog0001-.+\.png', dump_files)
        self.assertEquals(len(step_files), len(first_step_files), "There must be only one logging step in %s" % step_files)
        self.assertEquals(len(step_files), 3, "There must be 3 main files for the logging step in %s" % step_files)

        needles = self._get_matches_in('.*needle.*', step_files)
        self.assertEquals(len(needles), 1, "There must be one dumped needle in %s" % needles)
        self.assertIn('1needle', needles[0], "The needle must be enumerated in %s to achieve proper sorting" % needles[0])
        self.assertIn(needle_name, needles[0], "The needle %s must contain a detailed name '%s'" % (needles[0], needle_name))

        haystacks = self._get_matches_in('.*haystack.*', step_files)
        self.assertEquals(len(haystacks), 1, "There must be one dumped haystack in %s" % haystacks)
        self.assertIn('2haystack', haystacks[0], "The haystack must be enumerated in %s to achieve proper sorting" % haystacks[0])
        self.assertIn(haystack_name, haystacks[0], "The haystack %s must contain a detailed name '%s'" % (haystacks[0], haystack_name))

        hotmaps = self._get_matches_in('.*hotmap.*', step_files)
        self.assertEquals(len(hotmaps), 1, "There must be one dumped hotmap in %s" % hotmaps)
        self.assertIn('3hotmap', hotmaps[0], "The hotmap must be enumerated in %s to achieve proper sorting" % hotmaps[0])
        self.assertIn(backend, hotmaps[0], "The hotmap %s must report the used backend (%s)" % (hotmaps[0], backend))
        self.assertRegexpMatches(hotmaps[0], ".*-\d\.\d+.*", "The hotmap %s must report an achieved similarity" % hotmaps[0])

        match_files = self._get_matches_in('imglog\d\d\d\d-.+\.match', dump_files)
        self.assertEquals(len(match_files), 1, "There must be exactly one match file for the logging step in %s" % dump_files)
        self.assertEquals(match_files[0][:-6], needles[0][0:-4], "The match file %s must have the same name as the needle %s" %
                          (match_files[0], needles[0]))

        self.assertTrue(os.path.isfile(os.path.join(self.logpath, needles[0])), "The needle must be a regular file")
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, haystacks[0])), "The haystack must be a regular file")
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmaps[0])), "The hotmap must be a regular file")

        with open(os.path.join(self.logpath, match_files[0])) as match_settings:
            self.assertIn("[find]\nbackend = %s" % backend, match_settings.read(),
                          "The match settings must contain the configured backend (%s)" % backend)

    def test_template_match(self):
        self._test_simple_match("template")

    def test_feature_match(self):
        self._test_simple_match("feature")

    def test_findall_match(self):
        needle = Image('shape_red_box')
        haystack = Image('all_shapes')
        needle.use_own_settings = True
        settings = needle.match_settings
        settings.configure_backend(find_image="template")

        finder = ImageFinder()
        finder.find(needle, haystack, multiple=True)

        dump_files = os.listdir(self.logpath)
        self.assertEquals(len(dump_files), 6, "There must be a total of 6 different dumped files in %s" % dump_files)

        step_files = self._get_matches_in('imglog\d\d\d\d-.+\.png', dump_files)
        first_step_files = self._get_matches_in('imglog0001-.+\.png', dump_files)
        self.assertEquals(len(step_files), len(first_step_files), "There must be only one logging step in %s" % step_files)
        self.assertEquals(len(step_files), 5, "There must be 5 main files for the logging step in %s" % step_files)

        needles = self._get_matches_in('.*needle.*', step_files)
        self.assertEquals(len(needles), 1, "There must be one dumped needle in %s" % needles)
        self.assertIn('1needle', needles[0], "The needle must be enumerated in %s to achieve proper sorting" % needles[0])
        self.assertIn('shape_red_box', needles[0], "The needle %s must contain a detailed name 'shape_red_box'" % needles[0])

        haystacks = self._get_matches_in('.*haystack.*', step_files)
        self.assertEquals(len(haystacks), 1, "There must be one dumped haystack in %s" % haystacks)
        self.assertIn('2haystack', haystacks[0], "The haystack must be enumerated in %s to achieve proper sorting" % haystacks[0])
        self.assertIn('all_shapes', haystacks[0], "The haystack %s must contain a detailed name 'all_shapes'" % haystacks[0])

        hotmaps = self._get_matches_in('.*hotmap.*', step_files)
        self.assertEquals(len(hotmaps), 3, "There must be 3 dumped hotmaps in %s" % hotmaps)
        hotmaps = self._get_matches_in('.*3hotmap.*', step_files)
        self.assertEquals(len(hotmaps), 3, "All hotmaps must be enumerated in %s to achieve proper sorting" % hotmaps)
        hotmaps = self._get_matches_in('.*template.*', step_files)
        self.assertEquals(len(hotmaps), 3, "All hotmaps %s must report the used backend (template)" % hotmaps[0])
        hotmaps = self._get_matches_in('.*-\d\.\d+.*', step_files)
        self.assertEquals(len(hotmaps), 3, "All hotmaps %s must report the achieved similarity" % hotmaps[0])

        self.assertTrue(os.path.isfile(os.path.join(self.logpath, needles[0])), "The needle must be a regular file")
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, haystacks[0])), "The haystack must be a regular file")
        for i, hotmap in enumerate(sorted(hotmaps)):
            self.assertIn('template%s' % (i + 1), hotmap, "The hotmap %s must be enumerated to achieve proper hotmap sorting" % hotmap)
            self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)), "The hotmap %s must be a regular file" % hotmap)

    def test_hybrid_match(self):
        needle = Image('word')
        haystack = Image('sentence_font')
        needle.use_own_settings = True
        settings = needle.match_settings
        settings.configure_backend(find_image="hybrid")
        settings.p["find"]["front_similarity"].value = 0.3
        settings.p["find"]["similarity"].value = 0.6

        finder = ImageFinder()
        finder.find(needle, haystack)

        dump_files = os.listdir(self.logpath)
        self.assertEquals(len(dump_files), 10, "There must be a total of 10 different dumped files in %s" % dump_files)

        step_files = self._get_matches_in('imglog\d\d\d\d-.+\.png', dump_files)
        first_step_files = self._get_matches_in('imglog0001-.+\.png', dump_files)
        self.assertEquals(len(step_files), len(first_step_files), "There must be only one logging step in %s" % step_files)
        self.assertEquals(len(step_files), 9, "There must be 9 main files for the logging step in %s" % step_files)

        needles = self._get_matches_in('.*needle.*', step_files)
        self.assertEquals(len(needles), 1, "There must be one dumped needle in %s" % needles)
        self.assertIn('1needle', needles[0], "The needle must be enumerated in %s to achieve proper sorting" % needles[0])
        self.assertIn('word', needles[0], "The needle %s must contain a detailed name 'word'" % needles[0])

        haystacks = self._get_matches_in('.*haystack.*', step_files)
        self.assertEquals(len(haystacks), 1, "There must be one dumped haystack in %s" % haystacks)
        self.assertIn('2haystack', haystacks[0], "The haystack must be enumerated in %s to achieve proper sorting" % haystacks[0])
        self.assertIn('sentence_font', haystacks[0], "The haystack %s must contain a detailed name 'sentence_font'" % haystacks[0])

        hotmaps = self._get_matches_in('.*hotmap.*', step_files)
        self.assertEquals(len(hotmaps), 7, "There must be 7 dumped hotmaps in %s" % hotmaps)
        hotmaps = self._get_matches_in('.*3hotmap.*', step_files)
        self.assertEquals(len(hotmaps), 7, "All hotmaps must be enumerated in %s to achieve proper sorting" % hotmaps)
        hotmaps = self._get_matches_in('.*hybrid.*', step_files)
        self.assertEquals(len(hotmaps), 7, "All hotmaps %s must report the used backend (template)" % hotmaps[0])
        hotmaps = self._get_matches_in('.*-\d\.\d+.*', step_files)
        self.assertEquals(len(hotmaps), 7, "All hotmaps %s must report the achieved similarity" % hotmaps[0])

        self.assertTrue(os.path.isfile(os.path.join(self.logpath, needles[0])), "The needle must be a regular file")
        self.assertTrue(os.path.isfile(os.path.join(self.logpath, haystacks[0])), "The haystack must be a regular file")
        for i, hotmap in enumerate(sorted(hotmaps)):
            # print i, i%2, (i-1)/2+1
            if i == 0:
                self.assertNotIn('template', hotmap, "The main hotmap %s must not contain any internal backend" % hotmap)
                self.assertNotIn('feature', hotmap, "The main hotmap %s must not contain any internal backend" % hotmap)
            elif i % 2 == 1:
                self.assertIn('%sfeature' % ((i - 1) / 2 + 1), hotmap,
                              "The secondary hotmap %s must be enumerated to achieve proper hotmap sorting" % hotmap)
            else:
                self.assertIn('%stemplate' % ((i - 1) / 2 + 1), hotmap,
                              "The secondary hotmap %s must be enumerated to achieve proper hotmap sorting" % hotmap)
            self.assertTrue(os.path.isfile(os.path.join(self.logpath, hotmap)), "The hotmap %s must be a regular file" % hotmap)

        match_files = self._get_matches_in('imglog\d\d\d\d-.+\.match', dump_files)
        self.assertEquals(len(match_files), 1, "There must be exactly one match file for the logging step in %s" % dump_files)
        self.assertEquals(match_files[0][:-6], needles[0][0:-4], "The match file %s must have the same name as the needle %s" %
                          (match_files[0], needles[0]))
        with open(os.path.join(self.logpath, match_files[0])) as match_settings:
            self.assertIn("[find]\nbackend = hybrid", match_settings.read(),
                          "The match settings must contain the configured backend (hybrid)")


if __name__ == '__main__':
    unittest.main()
