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
# guibender public API: Used by the scripts.
# The import of this API file is injected before every script

import os, sys

my_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(my_dir, 'lib')
sys.path.insert(0, lib_dir)

from imagepath import ImagePath
from region import Region
from image import Image
from location import Location
from match import Match

sys.path.pop(0)

def add_image_path(directory):
    ImagePath().add_path(directory)

def remove_image_path(directory):
    ImagePath().remove_path(directory)

def exists(image_or_location, timeout=0):
    return Region().exists(image_or_location, timeout)
