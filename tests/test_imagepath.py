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

import os
import sys
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
        self.path = ImagePath()

        # Clear paths from any previous unit test since
        # the paths are shared between all ImagePath instances
        self.path.clear()

    def test_basic(self):
        self.path.add_path('paths')

    def test_remove_path(self):
        self.path.add_path('images')
        self.assertEqual(True, self.path.remove_path('images'))
        self.assertEqual(False, self.path.remove_path('images'))

    def test_remove_unknown_path(self):
        self.path.remove_path('foobar_does_not_exist')

    def test_search(self):
        self.path.add_path('images')
        self.assertEqual('images/shape_black_box.png', self.path.search('shape_black_box.png'))
        # Test without .png extension
        self.assertEqual('images/shape_black_box.png', self.path.search('shape_black_box'))

        # Create another ImagePath instance.
        # It should contain the same search paths
        new_finder = ImagePath()
        self.assertEqual('images/shape_black_box.png', new_finder.search('shape_black_box'))

    def test_search_target_error(self):
        try:
            target = self.path.search('foobar_does_not_exist')
            self.fail('Exception not thrown')
        except FileNotFoundError, e:
            pass

if __name__ == '__main__':
    unittest.main()
