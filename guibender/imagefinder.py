# Copyright 2013 Intranet AG / Thomas Jarosch and Plamen Dimitrov
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
            # TODO: since only the coordinates are available
            # and fuzzy areas of matches are returned we need
            # to ask autopy team for returning the matching rates
            # as well
            coord = autopy_screenshot.find_bitmap(autopy_needle, autopy_tolerance, ((xpos, ypos), (width, height)))

            if coord is not None:
                return Location(coord[0], coord[1])

        return None

    def find_all(self, haystack, needle, similarity, xpos, ypos, width, height):
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
            coords = autopy_screenshot.find_every_bitmap(autopy_needle, autopy_tolerance, ((xpos, ypos), (width, height)))
            print coords

            return [Location(*xy) for xy in coords]

        return None

import cv, cv2
import numpy
class BackendOpenCV:
    def find_image(self, haystack, needle, similarity, xpos, ypos,
                   width, height, nocolor = True):
        result = self._match(haystack, needle, nocolor)

        minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(result)
        logging.debug('minVal: %s', str(minVal))
        logging.debug('minLoc: %s', str(minLoc))
        logging.debug('maxVal (similarity): %s (%s)',
                      str(maxVal), similarity)
        logging.debug('maxLoc (x,y): %s', str(maxLoc))

        # TODO: Figure out how the threshold works
        # need to read openCV documentation
        if maxVal > similarity:
            return Location(maxLoc[0], maxLoc[1])

        return None

    def find_all(self, haystack, needle, similarity, xpos, ypos,
                 width, height, nocolor = True):
        result = self._match(haystack, needle, nocolor)

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

    def find_features(self, haystack, needle, similarity, nocolor = True):

        opencv_haystack = numpy.array(haystack.get_pil_image())
        opencv_haystack = opencv_haystack[:, :, ::-1].copy()            # Convert RGB to BGR

        opencv_needle = numpy.array(needle.get_pil_image())
        opencv_needle = opencv_needle[:, :, ::-1].copy()

        ngrey = cv2.cvtColor(opencv_needle, cv2.COLOR_BGR2GRAY)
        hgrey = cv2.cvtColor(opencv_haystack, cv2.COLOR_BGR2GRAY)

        # TODO: use these methods of the newer version
        # they offer multiple implementations of different feature detectors,
        # description extractors, and matchers all of which can be compared
        # and made available
        """
        # version test
        print cv2.__version__
        detector2 = cv2.FeatureDetector_create("SURF")

        extractor = cv2.DescriptorExtractor_create("SURF") #"BRIEF", etc
        matcher = cv2.DescriptorMatcher_create("BruteForce-Hamming")

        # keypoints
        haystack_keypoints = detector.detect(grey_haystack)
        needle_keypoints = detector.detect(grey_needle)

        # feature vectors (descriptors)
        (haystack_keypoints2, haystack_descriptors) = extractor.compute(grey_haystack, haystack_keypoints)
        (needle_keypoints2, needle_descriptors) = extractor.compute(grey_needle, needle_keypoints)

        # build matcher and match feature vectors
        matches = matcher.match(needle_descriptors, haystack_descriptors)
        # then extract matches above some similarity as done below
        """

        # build feature detector and descriptor extractor
        hessian_threshold = 85
        detector = cv2.SURF(hessian_threshold)
        (hkeypoints, hdescriptors) = detector.detect(hgrey, None, useProvidedKeypoints = False)
        (nkeypoints, ndescriptors) = detector.detect(ngrey, None, useProvidedKeypoints = False)

        # TODO: this MSER blob feature detector is also available in
        # the current cv2 module
        """
        detector = cv2.MSER()
        hregions = detector.detect(hgrey, None)
        nregions = detector.detect(ngrey, None)
        hhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in hregions]
        nhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in nregions]
        # show on final result
        cv2.polylines(opencv_haystack, hhulls, 1, (0, 255, 0))
        cv2.polylines(opencv_needle, nhulls, 1, (0, 255, 0))
        """

        if len(hkeypoints) < 4 or len(nkeypoints) < 4:
            raise IndexError("Minimum 4 features are required and less were detected "\
                             "with your needle size")

        # extract vectors of size 64 from raw descriptors numpy arrays
        rowsize = len(hdescriptors) / len(hkeypoints)
        hrows = numpy.array(hdescriptors, dtype = numpy.float32).reshape((-1, rowsize))
        nrows = numpy.array(ndescriptors, dtype = numpy.float32).reshape((-1, rowsize))
        #print hrows.shape, nrows.shape

        # kNN training - learn mapping from hrow to hkeypoints index
        samples = hrows
        responses = numpy.arange(len(hkeypoints), dtype = numpy.float32)
        #print len(samples), len(responses)
        knn = cv2.KNearest()
        knn.train(samples,responses)


        match_hkeypoints = []
        match_nkeypoints = []
        # retrieve index and value through enumeration
        for i, descriptor in enumerate(nrows):
            descriptor = numpy.array(descriptor, dtype = numpy.float32).reshape((1, 64))
            #print i, descriptor.shape, samples[0].shape
            retval, results, neigh_resp, dists = knn.find_nearest(descriptor, 1)
            res, dist =  int(results[0][0]), dists[0][0]
            #print res, dist

            # use similarity here
            if dist <= 1.0 - similarity:
                match_hkeypoints.append(hkeypoints[res])
                match_nkeypoints.append(nkeypoints[i])
            else:
                print "no", dist

        #print len(match_nkeypoints), len(match_hkeypoints)
        if len(match_hkeypoints) < 4 or len(match_nkeypoints) < 4:
            raise IndexError("Minimum 4 features are required and less were matched "\
                             "with your required similarity")
        H, mask = cv2.findHomography(numpy.array([nkp.pt for nkp in match_nkeypoints]),
                                     numpy.array([hkp.pt for hkp in match_hkeypoints]))

        (ocx, ocy) = (needle.get_width() / 2, needle.get_height() / 2)
        orig_center_wrapped = numpy.array([[[ocx, ocy]]], dtype = numpy.float32)
        #print orig_center_wrapped.shape, H.shape
        match_center_wrapped = cv2.perspectiveTransform(orig_center_wrapped, H)
        (mcx, mcy) = (match_center_wrapped[0][0][0], match_center_wrapped[0][0][1])

        # TODO: remove this code currently used for debugging
        # draw projected image center as well as matched and unmatched features
        cv2.circle(opencv_haystack, (int(mcx),int(mcy)), 2,(0,255,0),-1)
        cv2.circle(opencv_needle, (int(ocx),int(ocy)), 2,(0,255,0),-1)
        for hkp in hkeypoints:
            if hkp in match_hkeypoints:
                # draw matched keypoints in red color
                color = (0, 0, 255)
            else:
                # draw unmatched in blue color
                color = (255, 0, 0)
            # draw matched key points on original h image
            x,y = hkp.pt
            cv2.circle(opencv_haystack, (int(x),int(y)), 2, color, -1)
        for nkp in nkeypoints:
            if nkp in match_nkeypoints:
                # draw matched keypoints in red color
                color = (0, 0, 255)
            else:
                # draw unmatched in blue color
                color = (255, 0, 0)
            # draw matched key points on original n image
            x,y = nkp.pt
            cv2.circle(opencv_needle, (int(x),int(y)), 2, color, -1)
        cv2.imshow('haystack', opencv_haystack)
        cv2.imshow('needle', opencv_needle)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        return Location(int(mcx), int(mcy))

    def _match(self, haystack, needle, nocolor = True):
        # Sanity check: Needle size must be smaller than haystack
        if haystack.get_width() < needle.get_width() or haystack.get_height() < needle.get_height():
            logging.warning("The size of the searched image is smaller than its region - are you insane?")
            return None

        opencv_haystack = numpy.array(haystack.get_pil_image())
        opencv_haystack = opencv_haystack[:, :, ::-1].copy()            # Convert RGB to BGR

        opencv_needle = numpy.array(needle.get_pil_image())
        opencv_needle = opencv_needle[:, :, ::-1].copy()

        if nocolor:
            # convert to greyscale
            gray_haystack = cv2.cvtColor(opencv_haystack, cv2.COLOR_BGR2GRAY)
            gray_needle = cv2.cvtColor(opencv_needle, cv2.COLOR_BGR2GRAY)
            match = cv2.matchTemplate(gray_haystack, gray_needle, cv2.TM_CCOEFF_NORMED)
        else:
            match = cv2.matchTemplate(opencv_haystack, opencv_needle, cv2.TM_CCOEFF_NORMED)

        return match

    def measure_match_methods(self, haystack, needle):
        # Sanity check: Needle size must be smaller than haystack
        if haystack.get_width() < needle.get_width() or haystack.get_height() < needle.get_height():
            logging.warning("The size of the searched image is smaller than its region - are you insane?")
            return None

        opencv_haystack = numpy.array(haystack.get_pil_image())
        opencv_haystack = opencv_haystack[:, :, ::-1].copy()            # Convert RGB to BGR

        opencv_needle = numpy.array(needle.get_pil_image())
        opencv_needle = opencv_needle[:, :, ::-1].copy()

        # test all methods
        for method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED,
                       cv2.TM_CCORR, cv2.TM_CCORR_NORMED,
                       cv2.TM_CCOEFF, cv2.TM_CCOEFF_NORMED):
            for image in (needle, cv2.cvtColor(opencv_needle, cv2.COLOR_BGR2GRAY)):
                match = cv2.matchTemplate(opencv_haystack, opencv_needle, method)
                minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(match)
                print "%s,%s,%s,%s,%s,%s" % (needle.filename, method, minVal, maxVal, minLoc, maxLoc)

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

    def find_image(self, haystack, needle, similarity, xpos, ypos, width, height, nocolor = True):
        return self._backend.find_image(haystack, needle, similarity, xpos, ypos, width, height, nocolor)

    def find_all(self, haystack, needle, similarity, xpos, ypos, width, height, nocolor = True):
        return self._backend.find_all(haystack, needle, similarity, xpos, ypos, width, height, nocolor)
