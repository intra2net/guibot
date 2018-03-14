#!/usr/bin/python
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
import sys

unittest_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(unittest_dir, '..')
guibot_dir = os.path.join(main_dir, 'guibot')

# Add upper level 'guibot' directory to import path
# no matter from which directory we are called
sys.path.insert(0, guibot_dir)
