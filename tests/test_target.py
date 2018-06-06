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
from tempfile import NamedTemporaryFile

import common_test
from guibot.target import Image
from guibot.finder import Finder, CVParameter
from guibot.errors import *


class TargetTest(unittest.TestCase):

    def setUp(self):
        self.file_all_shapes = os.path.join(common_test.unittest_dir, 'images', 'all_shapes.png')

    def test_basic(self):
        image = Image(self.file_all_shapes)

        self.assertEqual(400, image.width)
        self.assertEqual(300, image.height)

        self.assertTrue(image.filename.find('all_shapes.png') is not -1)
        self.assertIsInstance(image.match_settings, Finder)
        self.assertFalse(image.use_own_settings)

    def test_copy_object(self):
        image = Image(self.file_all_shapes)

        my_copy = image.copy()
        self.assertNotEqual(image.match_settings, my_copy.match_settings)
        self.assertEqual(image.filename, my_copy.filename)
        self.assertEqual(image.similarity, my_copy.similarity)
        self.assertEqual(image.pil_image, my_copy.pil_image)
        self.assertEqual(image.width, my_copy.width)
        self.assertEqual(image.height, my_copy.height)
        self.assertEqual(image.center_offset, my_copy.center_offset)

    def test_center_offset(self):
        image = Image(self.file_all_shapes)

        center_offset = image.center_offset
        self.assertEqual(0, center_offset.x)
        self.assertEqual(0, center_offset.y)

        new_image = image.with_center_offset(100, 30)
        self.assertEqual(image.filename, new_image.filename)
        self.assertEqual(image.similarity, new_image.similarity)
        self.assertEqual(image.pil_image, new_image.pil_image)
        self.assertEqual(image.width, new_image.width)
        self.assertEqual(image.height, new_image.height)
        self.assertNotEqual(image.center_offset, new_image.center_offset)

        center_offset = new_image.center_offset
        self.assertEqual(100, center_offset.x)
        self.assertEqual(30, center_offset.y)

        # check it's unchanged in the original
        center_offset = image.center_offset
        self.assertEqual(0, center_offset.x)
        self.assertEqual(0, center_offset.y)

    def test_similarity(self):
        image = Image(self.file_all_shapes)

        new_image = image.with_similarity(0.45)
        self.assertEqual(0.45, new_image.similarity)
        # TODO: create a separate config for defaults to extract this from there
        self.assertEqual(0.8, image.similarity)

        self.assertEqual(image.filename, new_image.filename)
        self.assertNotEqual(image.similarity, new_image.similarity)
        self.assertEqual(image.pil_image, new_image.pil_image)
        self.assertEqual(image.width, new_image.width)
        self.assertEqual(image.height, new_image.height)
        self.assertEqual(image.center_offset, new_image.center_offset)

    def test_save(self):
        image = Image(self.file_all_shapes)

        with NamedTemporaryFile(prefix='guibot', suffix='.png') as f:
            returned_image = image.save(f.name)
            loaded_image = Image(f.name)

            self.assertEqual(returned_image.filename, loaded_image.filename)
            self.assertEqual(image.width, loaded_image.width)
            self.assertEqual(image.height, loaded_image.height)

            image.use_own_settings = True
            returned_image = image.save(f.name)
            loaded_image = Image(f.name)
            os.unlink("%s.match" % f.name[:-4])

            for category in returned_image.match_settings.params.keys():
                self.assertIn(category, loaded_image.match_settings.params.keys())
                for key in returned_image.match_settings.params[category].keys():
                    self.assertIn(key, loaded_image.match_settings.params[category])
                    if not isinstance(returned_image.match_settings.params[category][key], CVParameter):
                        self.assertEqual(returned_image.match_settings.params[category][key],
                                         loaded_image.match_settings.params[category][key])
                        continue
                    self.assertAlmostEqual(returned_image.match_settings.params[category][key].value,
                                           loaded_image.match_settings.params[category][key].value)
                    self.assertEqual(returned_image.match_settings.params[category][key].range[0],
                                     loaded_image.match_settings.params[category][key].range[0])
                    self.assertEqual(returned_image.match_settings.params[category][key].range[1],
                                     loaded_image.match_settings.params[category][key].range[1])
                    self.assertEqual(returned_image.match_settings.params[category][key].delta,
                                     loaded_image.match_settings.params[category][key].delta)
                    self.assertEqual(returned_image.match_settings.params[category][key].tolerance,
                                     loaded_image.match_settings.params[category][key].tolerance)
                    self.assertEqual(returned_image.match_settings.params[category][key].fixed,
                                     loaded_image.match_settings.params[category][key].fixed)

    def test_nonexisting_image(self):
        try:
            image = Image('foobar_does_not_exist')
            self.fail('Exception not thrown')
        except FileNotFoundError:
            pass

    def test_image_cache(self):
        image = Image(self.file_all_shapes)

        second_image = Image(self.file_all_shapes)
        self.assertIs(image.pil_image, second_image.pil_image)

        # Clear image cache the hard way
        Image()._cache.clear()

        third_image = Image(self.file_all_shapes)
        self.assertIsNot(image.pil_image, third_image.pil_image)

if __name__ == '__main__':
    unittest.main()
