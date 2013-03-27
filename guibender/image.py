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

    _cache = {}

    def __init__(self, image_filename=None, pil_image=None, match_settings=None):
        self.filename = image_filename
        self.match_settings = match_settings
        self.pil_image = pil_image

        if self.match_settings != None:
            self.use_own_settings = True
        else:
            self.use_own_settings = False
        self.width = 0
        self.height = 0
        self.target_center_offset = Location(0, 0)

        if self.filename is not None and (pil_image is None or match_settings is None):
            if not os.path.exists(self.filename):
                self.filename = ImagePath().search(self.filename)

            if pil_image is None:
                if self.filename in self._cache:
                    self.pil_image = self._cache[self.filename]
                else:
                    # load and cache image
                    self.pil_image = PIL.Image.open(self.filename).convert('RGB')
                    self._cache[self.filename] = self.pil_image
            if match_settings is None:
                match_file = self.filename[:-4] + ".match"
                #print match_file, self.filename
                if not os.path.exists(match_file):
                    self.match_settings = CVEqualizer()
                else:
                    self.match_settings = CVEqualizer()
                    self.match_settings.from_match_file(self.filename[:-4])
                    self.use_own_settings = True

        # Set width and height
        if self.pil_image:
            self.width = self.pil_image.size[0]
            self.height = self.pil_image.size[1]

    def copy(self):
        copy_settings = copy.deepcopy(self.match_settings)
        selfcopy = copy.copy(self)
        selfcopy.match_settings = copy_settings
        return selfcopy

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
        if self.use_own_settings:
            self.match_settings.to_match_file(filename[:-4])

        new_image = self.copy()
        new_image.filename = filename

        return new_image
