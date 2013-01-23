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

import os, sys
import unittest
import common_test

from imagepath import ImagePath
from errors import *

class ImagePathTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Change to 'tests' directory
        self.saved_working_dir = os.getcwd()
        os.chdir(common_test.unittest_dir)

    @classmethod
    def tearDownClass(self):
        os.chdir(self.saved_working_dir)

    def setUp(self):
        self.imagepath = ImagePath()

    def test_basic(self):
        self.imagepath.add_path('images')

    def test_remove_path(self):
        self.imagepath.add_path('images')
        self.assertEqual(True, self.imagepath.remove_path('images'))
        # No longer in imagefinder
        self.assertEqual(False, self.imagepath.remove_path('images'))

    def test_remove_unknown_path(self):
        self.imagepath.remove_path('foobar_does_not_exist')

    def test_search(self):
        self.imagepath.add_path('images')
        self.assertEqual('images/qt4gui_button.png', self.imagepath.search('qt4gui_button.png'))
        # Test without .png extension
        self.assertEqual('images/qt4gui_button.png', self.imagepath.search('qt4gui_button'))

        # Create another ImagePath instance.
        # It should contain the same search paths
        new_finder = ImagePath()
        self.assertEqual('images/qt4gui_button.png', new_finder.search('qt4gui_button'))

    def test_find_image_error(self):
        try:
            image = self.imagepath.search('foobar_does_not_exist')
            self.fail('Exception not thrown')
        except FileNotFoundError, e:
            pass

if __name__ == '__main__':
    unittest.main()
