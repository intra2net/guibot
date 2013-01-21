#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch
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

import unittest
import sys
sys.path.append('../lib')

from tempfile import NamedTemporaryFile
from image import Image
from errors import *

class ImageTest(unittest.TestCase):
    def setUp(self):
        self.example_dir = '../examples/images/'

    def test_basic(self):
        image = Image(self.example_dir + 'all_shapes.png')

        self.assertEqual(400, image.get_width())
        self.assertEqual(300, image.get_height())

        self.assertTrue(image.get_filename().find('all_shapes.png') is not -1)
        self.assertEqual(Image.DEFAULT_SIMILARITY, image.get_similarity())

    def test_copy_object(self):
        image = Image(self.example_dir + 'all_shapes.png')

        my_copy = image.copy()
        self.assertEqual(image.filename, my_copy.filename)
        self.assertEqual(image.img_similarity, my_copy.img_similarity)
        self.assertEqual(image.pil_image, my_copy.pil_image)
        self.assertEqual(image.width, my_copy.width)
        self.assertEqual(image.height, my_copy.height)
        self.assertEqual(image.target_center_offset, my_copy.target_center_offset)

    def test_target_offset(self):
        image = Image(self.example_dir + 'all_shapes.png')

        target_offset = image.get_target_offset()
        self.assertEqual(0, target_offset.get_x())
        self.assertEqual(0, target_offset.get_y())

        new_image = image.target_offset(100, 30)
        self.assertEqual(image.filename, new_image.filename)
        self.assertEqual(image.img_similarity, new_image.img_similarity)
        self.assertEqual(image.pil_image, new_image.pil_image)
        self.assertEqual(image.width, new_image.width)
        self.assertEqual(image.height, new_image.height)
        self.assertNotEqual(image.target_center_offset, new_image.target_center_offset)

        target_offset = new_image.get_target_offset()
        self.assertEqual(100, target_offset.get_x())
        self.assertEqual(30, target_offset.get_y())

        # check it's unchanged in the original
        target_offset = image.get_target_offset()
        self.assertEqual(0, target_offset.get_x())
        self.assertEqual(0, target_offset.get_y())

    def test_similarity(self):
        image = Image(self.example_dir + 'all_shapes.png')

        new_image = image.similarity(0.45)
        self.assertEqual(0.45, new_image.get_similarity())
        self.assertEqual(Image.DEFAULT_SIMILARITY, image.get_similarity())

        self.assertEqual(image.filename, new_image.filename)
        self.assertNotEqual(image.img_similarity, new_image.img_similarity)
        self.assertEqual(image.pil_image, new_image.pil_image)
        self.assertEqual(image.width, new_image.width)
        self.assertEqual(image.height, new_image.height)
        self.assertEqual(image.target_center_offset, new_image.target_center_offset)

    def test_exact(self):
        image = Image(self.example_dir + 'all_shapes.png')

        new_image = image.exact()
        self.assertEqual(1.0, new_image.get_similarity())
        self.assertEqual(Image.DEFAULT_SIMILARITY, image.get_similarity())

    def test_save(self):
        image = Image(self.example_dir + 'all_shapes.png')

        with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
            returned_image = image.save(f.name)
            loaded_image = Image(f.name)

            self.assertEqual(returned_image.filename, loaded_image.filename)
            self.assertEqual(image.width, loaded_image.width)
            self.assertEqual(image.height, loaded_image.height)

    def test_nonexisting_image(self):
        try:
            image = Image('foobar_does_not_exist')
            self.fail('Exception not thrown')
        except FileNotFoundError:
            pass

    def test_image_cache(self):
        image = Image(self.example_dir + 'all_shapes.png')

        second_image = Image(self.example_dir + 'all_shapes.png')
        self.assertEqual(image.get_pil_image(), second_image.get_pil_image())

        # Clear image cache the hard way
        Image()._cache.clear()

        third_image = Image(self.example_dir + 'all_shapes.png')
        self.assertNotEqual(image.get_pil_image(), third_image.get_pil_image())

if __name__ == '__main__':
    unittest.main()
