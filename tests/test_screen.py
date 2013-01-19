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

from region import Region
from screen import Screen

class RegionTest(unittest.TestCase):
    def test_basic(self):
        screen = Screen()

        self.assertTrue(screen.get_width() > 0)
        self.assertTrue(screen.get_height() > 0)

if __name__ == '__main__':
    unittest.main()
