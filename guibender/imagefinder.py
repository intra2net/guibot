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
import logging
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

import cv, cv2
import numpy
class BackendOpenCV:
    def find_image(self, haystack, needle, similarity, xpos, ypos, width, height):
        result = self._match(haystack, needle)

        minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(result)
        logging.debug('minVal: %s', str(minVal))
        logging.debug('minLoc: %s', str(minLoc))
        logging.debug('maxVal (similarity): %s (%s)', str(maxVal), similarity)
        logging.debug('maxLoc (x,y): %s', str(maxLoc))

        # TODO: Figure out how the threshold works
        # need to read openCV documentation
        if maxVal > similarity:
            return Location(maxLoc[0], maxLoc[1])

        return None

    def find_all(self, haystack, needle, similarity, xpos, ypos, width, height):
        result = self._match(haystack, needle)

        # variant 1: extract all matches above required similarity
        # problems: clouds of matches (like electron clouds), too slow
        """
        locations = []
        for i in range(len(result)):
            for j in range(len(result[i])):
                if result[i][j] > similarity:
                    locations.append((j, i))
        print locations
        max_loc = (None, 0.0)
        for l in locations:
            if result[l[1], l[0]] > max_loc[1]:
                max_loc = ((l[0], l[1]), result[l[1], l[0]])
        print max_loc
        """

        # variant 2: extract all matches above required similarity
        # problems: trims everything, still more matches then desired are left
        #result = cv2.threshold(result, similarity, 1.0, cv.CV_THRESH_BINARY)
        #print result

        # variant 3: extract all discrete function maxima
        # problems: rigged match areas with multiple neighboring maxima
        # instead of analytic functions
        """
        maxima = []
        for i in range(1, len(result) - 1):
            for j in range(1, len(result[i]) - 1):
                if result[i][j] > 0.0:
                    if (result[i][j] > result[i+1][j] and
                        result[i][j] > result[i-1][j] and
                        result[i][j] > result[i][j+1] and
                        result[i][j] > result[i][j-1]):
                        maxima.append(((j, i), result[i][j]))
        print len(maxima)
        """

        # variant 4: extract maxima once for each needle size
        # working but needs unit tests
        maxima = []
        while True:
            minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(result)
            if maxVal < similarity:
                break

            logging.debug('Found a match with:')
            #logging.debug('minVal: %s', str(minVal))
            #logging.debug('minLoc: %s', str(minLoc))
            logging.debug('maxVal (similarity): %s (%s)', str(maxVal), similarity)
            logging.debug('maxLoc (x,y): %s', str(maxLoc))

            maxima.append(Location(maxLoc[0], maxLoc[1]))

            res_w = haystack.width - needle.width + 1
            res_h = haystack.height - needle.height + 1
            match_x0 = max(maxLoc[0] - int(0.5 * needle.width), 0)
            match_x1 = min(maxLoc[0] + int(0.5 * needle.width), res_w)
            match_y0 = max(maxLoc[1] - int(0.5 * needle.height), 0)
            match_y1 = min(maxLoc[1] + int(0.5 * needle.height), len(result[0]))

            logging.debug("Wipe image matches in x [%s, %s]\[%s, %s]",
                          match_x0, match_x1, 0, res_w)
            logging.debug("Wipe image matches in y [%s, %s]\[%s, %s]",
                          match_y0, match_y1, 0, res_h)

            # clean found image to look for next safe distance match
            for i in range(max(maxLoc[0] - int(0.5 * needle.width), 0),
                           min(maxLoc[0] + int(0.5 * needle.width), res_w)):
                for j in range(max(maxLoc[1] - int(0.5 * needle.height), 0),
                               min(maxLoc[1] + int(0.5 * needle.height), res_h)):

                    #print haystack.width, needle.width, maxLoc[0], maxLoc[0] - int(0.5 * needle.width), max(maxLoc[0] - int(0.5 * needle.width), 0)
                    #print haystack.width, needle.width, maxLoc[0], maxLoc[0] + int(0.5 * needle.width), min(maxLoc[0] + int(0.5 * needle.width), 0)
                    #print haystack.height, needle.height, maxLoc[1], maxLoc[1] - int(0.5 * needle.height), max(maxLoc[1] - int(0.5 * needle.height), 0)
                    #print haystack.height, needle.height, maxLoc[1], maxLoc[1] + int(0.5 * needle.height), min(maxLoc[1] + int(0.5 * needle.height), 0)
                    #print "index at ", j, i, " in ", len(result), len(result[0])

                    result[j][i] = 0.0
            logging.debug("Total maxima up to the point are %i", len(maxima))
            logging.debug("maxLoc was %s and is now %s", maxVal, result[maxLoc[1], maxLoc[0]])
        logging.info("%i matches found" % len(maxima))

        # variant 5: stackoverflow solution
        # For multiple matches (seen on stackoverflow)
        #match_indices = numpy.arange(result.size)[(result>similarity).flatten()]
        #print match_indices
        #all_matches = numpy.unravel_index(match_indices,result.shape)
        #print all_matches

        return maxima

    def _match(self, haystack, needle):
        # Sanity check: Needle size must be smaller than haystack
        if haystack.get_width() < needle.get_width() or haystack.get_height() < needle.get_height():
            logging.warning("The size of the searched image is smaller than its region - are you insane?")
            return None

        opencv_haystack = numpy.array(haystack.get_pil_image())
        opencv_haystack = opencv_haystack[:, :, ::-1].copy()            # Convert RGB to BGR

        opencv_needle = numpy.array(needle.get_pil_image())
        opencv_needle = opencv_needle[:, :, ::-1].copy()

        match = cv2.matchTemplate(opencv_haystack,opencv_needle,cv2.TM_CCOEFF_NORMED)
        return match

class ImageFinder:
    _backend = None

    def __init__(self, backend='auto'):
        if backend is 'auto':
            try:
                # TODO: Test 'import cv'
                self._backend = BackendOpenCV()
            except:
                self._backend = BackendAutoPy()
        elif backend is 'opencv':
            self._backend = BackendOpenCV()
        elif backend is 'autopy':
            self._backend = BackendAutoPy()
        else:
            raise ImageFinderBackendError('Unsupported backend: ' + backend)

    def find_image(self, haystack, needle, similarity, xpos, ypos, width, height):
        return self._backend.find_image(haystack, needle, similarity, xpos, ypos, width, height)

    def find_all(self, haystack, needle, similarity, xpos, ypos, width, height):
        return self._backend.find_all(haystack, needle, similarity, xpos, ypos, width, height)
