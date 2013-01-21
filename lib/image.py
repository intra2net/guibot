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
import autopy.bitmap
import os
from location import Location
from imagepath import ImagePath

class Image:
    DEFAULT_SIMILARITY = 0.8

    _cache = {}

    def __init__(self, image_filename=None, similarity=DEFAULT_SIMILARITY, backend_data=None):
        self.filename = image_filename
        self.img_similarity = similarity
        self.backend_data = backend_data

        self.width = 0
        self.height = 0
        self.target_center_offset = Location(0, 0)

        if self.filename is not None and backend_data is None:
            if not os.path.exists(self.filename):
                self.filename = ImagePath().search(self.filename)

            if self.filename in self._cache:
                self.backend_data = self._cache[self.filename]
            else:
                # load and cache image
                # TODO: Abstract out autopy backend into separate backend class
                self.backend_data = autopy.bitmap.Bitmap.open(self.filename)
                self._cache[self.filename] = self.backend_data

        # Set width and height
        if self.backend_data:
            self.width = self.backend_data.width
            self.height = self.backend_data.height

    def copy(self):
        return copy.copy(self)

    def get_filename(self):
        return self.filename;

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_backend_data(self):
        return self.backend_data

    def get_similarity(self):
        return self.img_similarity

    def similarity(self, new_similarity):
        new_image = self.copy()

        new_image.img_similarity = new_similarity
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
        self.backend_data.save(filename)

        new_image = self.copy()
        new_image.filename = filename

        return new_image
