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

from imagefinder import ImageFinder
from errors import *

class ImageFinderTest(unittest.TestCase):
    def setUp(self):
        self.finder = ImageFinder()

    def test_basic(self):
        self.finder.add_path('images')

    def test_remove_path(self):
        self.finder.add_path('images')
        self.assertEqual(True, self.finder.remove_path('images'))
        # No longer in imagefinder
        self.assertEqual(False, self.finder.remove_path('images'))

    def test_remove_unknown_path(self):
        self.finder.remove_path('foobar_does_not_exist')

    def test_search(self):
        self.finder.add_path('images')
        self.assertEqual('images/qt4gui_button.png', self.finder.search('qt4gui_button.png'))
        # Test without .png extension
        self.assertEqual('images/qt4gui_button.png', self.finder.search('qt4gui_button'))

        # Create another ImageFinder instance.
        # It should contain the same search paths
        new_finder = ImageFinder()
        self.assertEqual('images/qt4gui_button.png', new_finder.search('qt4gui_button'))

    def test_find_image_error(self):
        try:
            image = self.finder.search('foobar_does_not_exist')
            self.fail('Exception not thrown')
        except FileNotFoundError, e:
            pass

if __name__ == '__main__':
    unittest.main()
