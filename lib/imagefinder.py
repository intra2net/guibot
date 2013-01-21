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
import PIL.Image
from tempfile import NamedTemporaryFile

from location import Location
from errors import *

from autopy import bitmap

class BackendAutoPy:
    _bitmapcache = {}

    def find_image(self, haystack, needle, similarity, xpos, ypos, width, height):
        if needle.get_filename() in self._bitmapcache:
            autopy_needle = self._bitmapcache[needle.get_filename()]
        else:
            # load and cache it
            # TODO: Use in-memory conversion
            autopy_needle = bitmap.Bitmap.open(needle.get_filename())
            self._bitmapcache[needle.get_filename()] = autopy_needle

        # TODO: Use in-memory conversion
        with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
            haystack.save(f.name)
            autopy_screenshot = bitmap.Bitmap.open(f.name)

            autopy_tolerance = 1.0 - similarity
            coord = autopy_screenshot.find_bitmap(autopy_needle, autopy_tolerance, ((xpos, ypos), (width, height)))

            if coord is not None:
                return Location(coord[0], coord[1])

        return None

class ImageFinder:
    _backend = None

    def __init__(self, backend='auto'):
        if backend is not 'auto' and self._backend is not None:
            raise ImageFinderBackendError('_backend already initialized')

        if self._backend is None:
            # Currently autopy is implemented only
            self._backend = BackendAutoPy()

    def find_image(self, haystack, needle, similarity, xpos, ypos, width, height):
        return self._backend.find_image(haystack, needle, similarity, xpos, ypos, width, height)
