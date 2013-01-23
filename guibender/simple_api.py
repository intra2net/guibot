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
# guibender simple, procedural API.
# Creates an internal GuiBender() object.

import os, sys

from imagepath import ImagePath
from region import Region
from image import Image
from location import Location
from match import Match
from guibender import GuiBender

guibender = GuiBender()
region = guibender.get_region()

# return main guibender object
def get_guibender():
    return guibender

def add_image_path(directory):
    ImagePath().add_path(directory)

def remove_image_path(directory):
    ImagePath().remove_path(directory)

def exists(image_or_location, timeout=0):
    return region.exists(image_or_location, timeout)
