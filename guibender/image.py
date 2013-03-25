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
import copy
import os
import logging
import PIL.Image

from location import Location
from imagepath import ImagePath
from cvequalizer import CVEqualizer

class Image:
    DEFAULT_SIMILARITY = 0.8

    _cache = {}

    def __init__(self, image_filename=None, similarity=DEFAULT_SIMILARITY, pil_image=None):
        self.filename = image_filename
        self.match_settings = CVEqualizer()
        self.match_settings.p["find"]["similarity"].value = similarity
        self.pil_image = pil_image

        self.width = 0
        self.height = 0
        self.target_center_offset = Location(0, 0)

        if self.filename is not None and pil_image is None:
            if not os.path.exists(self.filename):
                self.filename = ImagePath().search(self.filename)

            if self.filename in self._cache:
                self.pil_image = self._cache[self.filename]
            else:
                # load and cache image
                self.pil_image = PIL.Image.open(self.filename).convert('RGB')
                self._cache[self.filename] = self.pil_image

        # Set width and height
        if self.pil_image:
            self.width = self.pil_image.size[0]
            self.height = self.pil_image.size[1]

    def copy(self):
        return copy.copy(self)

    def get_filename(self):
        return self.filename;

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_pil_image(self):
        return self.pil_image

    def get_similarity(self):
        return self.match_settings.p["find"]["similarity"].value

    def similarity(self, new_similarity):
        new_image = self.copy()

        new_image.match_settings.p["find"]["similarity"].value = new_similarity
        return new_image

    def get_gray(self):
        return self.match_settings.p["find"]["nocolor"].value

    def gray(self, new_nocolor):
        new_image = self.copy()

        new_image.match_settings.p["find"]["nocolor"].value = new_nocolor
        return new_image

    def exact(self):
        return self.similarity(1.0)

    def target_offset(self, xpos, ypos):
        new_image = self.copy()

        new_image.target_center_offset = Location(xpos, ypos)
        return new_image

    def get_target_offset(self):
        return self.target_center_offset

    def save(self, filename):
        self.pil_image.save(filename)

        new_image = self.copy()
        new_image.filename = filename

        return new_image
