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
import autopy.bitmap
from image import Image
from errors import *

class ImageFinder:
    _imageCache = {}
    _imageDirs = []

    def add_path(self, directory):
        if directory not in self._imageDirs:
            self._imageDirs.append(directory)

    def remove_path(self, directory):
        try:
            self._imageDirs.remove(directory)
        except:
            return False

        return True

    def search_filename(self, filename):
        for dir in self._imageDirs:
            fullname = os.path.join(dir, filename)
            if os.path.exists(fullname):
                return fullname

            # Check with .png extension
            fullname = os.path.join(dir, filename + '.png')
            if os.path.exists(fullname):
                return fullname

        return None

    def find_image(self, filename):
        if filename in self._imageCache:
            return self._imageCache[filename]

        fullpath = self.search_filename(filename)
        if fullpath is None:
            raise FileNotFoundError('File ' + filename + ' not found')

        self._imageCache[filename] = Image(fullpath)
        return self._imageCache[filename]
