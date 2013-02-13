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
import cv, cv2
import numpy


class ImageFinder:

    def __init__(self):
        """
        Initiate the image finder with default algorithm configuration.

        template matchers:
            autopy, sqdiff, ccorr, ccoeff
            sqdiff_normed, *ccorr_normed, ccoeff_normed

        feature detectors:
            FAST, STAR, SIFT, SURF, ORB, MSER,
            GFTT, HARRIS, Dense, SimpleBlob
            GridFAST, GridSTAR, ...
            PyramidFAST, PyramidSTAR, ...

        feature extractors:
            SIFT, SURF, ORB, BRIEF, FREAK, in-house

        feature matchers:
            BruteForce, BruteForce-L1, BruteForce-Hamming,
            BruteForce-Hamming(2), FlannBased, in-house

        Starred methods are currently known to be buggy.

        The image logging consists of saving the last hotmap.

        If the template matching method was used, the hotmap is
        a fingerprint of the matching in the entire haystack. Its
        lighter areas are places where the needle was matched better.

        If the feature matching method was used, the hotmap contains
        the matched needle features in the haystack (green), the ones
        that were not matched (red), and the calculated focus point
        that would be used for clicking, hovering, etc. (blue).
        """
        # currently fully compatible methods
        self.template_matchers = ("autopy", "sqdiff", "ccorr", "ccoeff",
                                  "sqdiff_normed", "ccorr_normed", "ccoeff_normed")
        self.feature_matchers = ("BruteForce-Hamming", "BruteForce-Hamming(2)", "in-house")
        self.feature_detectors = ("ORB", "in-house")
        self.feature_extractors = ("ORB", "BRIEF")

        self.match_template = "ccoeff_normed"
        self.detect_features = "ORB"
        self.extract_features = "BRIEF"
        self.match_features = "BruteForce-Hamming"

        self._bitmapcache = {}
        self.image_logging = False

    def find_image(self, haystack, needle, similarity, xpos, ypos,
                   width, height, nocolor = True):
        """
        Finds a needle image in a haystack image using template matching.

        Returns a Location object for the match or None in not found.
        Available template matching methods are: autopy, opencv
        """
        if self.match_template not in self.template_matchers:
            raise ImageFinderMethodError

        elif self.match_template == "autopy":
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
                coord = autopy_screenshot.find_bitmap(autopy_needle, autopy_tolerance,
                                                      ((xpos, ypos), (width, height)))

                if coord is not None:
                    return Location(coord[0], coord[1])
            return None

        else:
            result = self._match_template(haystack, needle, nocolor, self.match_template)

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
        """
        Finds all needle images in a haystack image using template matching.

        Returns a list of Location objects for all matches or None in not found.
        Available template matching methods are: opencv
        """
        if self.match_template not in self.template_matchers:
            raise ImageFinderMethodError
        # autopy template matching for find_all is replaced by ccoeff_normed
        # since it is inefficient and returns match clouds
        if self.match_template == "autopy":
            match_template = "ccoeff_normed"
        else:
            match_template = self.match_template
        result = self._match_template(haystack, needle, nocolor, match_template)

        # extract maxima once for each needle size region
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

        return maxima

    def find_features(self, haystack, needle, similarity, nocolor = True):
        """
        Finds a needle image in a haystack image using feature matching.

        Returns a Location object for the match or None in not found.
        Available methods include a combination of feature detector,
        extractor, and matcher.
        """
        # TODO: test all methods
        # TODO: multichannel matching using the color option
        hkp, hdc, nkp, ndc = self._detect_features(haystack, needle,
                                                   detect = self.detect_features,
                                                   extract = self.extract_features)
        mhkp, hkp, mnkp, nkp = self._match_features(hkp, hdc, nkp, ndc,
                                                    similarity, self.match_features)
        #print "%s\\%s" % (len(mhkp), len(hkp)), "%s\\%s" % (len(mnkp), len(nkp))

        if self.image_logging:
            hotmap, _ = self._get_opencv_images(haystack, needle)
            for kp in hkp:
                if kp in mhkp:
                    color = (0, 0, 255)
                else:
                    color = (0, 255, 0)
                x, y = kp.pt
                cv2.circle(hotmap, (int(x),int(y)), 2, color, -1)

        if len(mhkp) > 4 or len(mnkp) > 4:
            H, mask = cv2.findHomography(numpy.array([kp.pt for kp in mnkp]),
                                         numpy.array([kp.pt for kp in mhkp]),
                                         cv2.RANSAC, 10.0)

            (ocx, ocy) = (needle.get_width() / 2, needle.get_height() / 2)
            orig_center_wrapped = numpy.array([[[ocx, ocy]]], dtype = numpy.float32)
            #print orig_center_wrapped.shape, H.shape
            match_center_wrapped = cv2.perspectiveTransform(orig_center_wrapped, H)
            (mcx, mcy) = (match_center_wrapped[0][0][0], match_center_wrapped[0][0][1])

            if self.image_logging:
                # hotmap should already be defined so careful with the line above
                cv2.circle(hotmap, (int(mcx),int(mcy)), 2, (255,0,0), -1)
                cv2.imwrite("last_hotmap.png", hotmap)

            return Location(int(mcx), int(mcy))

        else:
            # minimum 4 features are required for calculating the homography matrix
            #raise IndexError("Minimum 4 features are required while %s\\%s from needle "\
            #                 "and %s\\%s from haystack were matched with your required "\
            #                 "similarity and image size" % (len(mhkp), len(hkp),
            #                                                len(mnkp), len(nkp)))
            return None

    def benchmark_find(self, haystack, needle):
        """
        Returns a list of (method, success, coordinates) tuples sorted in
        descending order with all available image matching methods.

        Keep in mind that the success is not scaled and methods that are
        not normalized will be returned first.

        Methods that are supported by OpenCV but currently don't worked are
        excluded from the dictionary. The dictionary can thus also be used
        to assess what are the available methods and their success for a given
        needle and haystack.

        TODO: This method should soon be able to include feature matching methods
        in the comparison. After all the idea is to benchmark ALL working ways to
        find a given needle in a given haystack.
        """
        results = []
        # test all template matching methods
        for key in self.template_matchers:

            # autopy does not provide any similarity value therefore cannot be compared
            if key == "autopy":
                continue

            for gray in (True, False):
                if gray:
                    method = key + "_gray"
                    #match = cv2.matchTemplate(gray_haystack, gray_needle, methods[key])
                else:
                    method = key
                    #match = cv2.matchTemplate(opencv_haystack, opencv_needle, methods[key])

                match = self._match_template(haystack, needle, gray, key)
                minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(match)

                #print "%s,%s,%s,%s,%s,%s" % (needle.filename, method, minVal, maxVal, minLoc, maxLoc)
                if key in ("sqdiff", "sqdiff_normed"):
                    success = 1 - minVal
                    location = minLoc
                else:
                    success = maxVal
                    location = maxLoc

                results.append((method, success, location))
        return sorted(results, key = lambda x: x[1], reverse = True)

    def _detect_features(self, haystack, needle, detect, extract):
        hgray, ngray = self._get_opencv_images(haystack, needle, gray = True)

        if detect == "in-house":
            # build the old surf feature detector
            hessian_threshold = 85
            detector = cv2.SURF(hessian_threshold)

            (hkeypoints, hdescriptors) = detector.detect(hgray, None, useProvidedKeypoints = False)
            (nkeypoints, ndescriptors) = detector.detect(ngray, None, useProvidedKeypoints = False)

            # TODO: this MSER blob feature detector is also available in
            # version 2.2.3
            """
            detector = cv2.MSER()
            hregions = detector.detect(hgray, None)
            nregions = detector.detect(ngray, None)
            hhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in hregions]
            nhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in nregions]
            # show on final result
            cv2.polylines(opencv_haystack, hhulls, 1, (0, 255, 0))
            cv2.polylines(opencv_needle, nhulls, 1, (0, 255, 0))
            """

        # include only methods tested for compatibility
        elif detect in self.feature_detectors and extract in self.feature_extractors:
            detector = cv2.FeatureDetector_create(detect)
            extractor = cv2.DescriptorExtractor_create(extract)

            # keypoints
            hkeypoints = detector.detect(hgray)
            nkeypoints = detector.detect(ngray)

            # feature vectors (descriptors)
            (hkeypoints, hdescriptors) = extractor.compute(hgray, hkeypoints)
            (nkeypoints, ndescriptors) = extractor.compute(ngray, nkeypoints)

        else:
            raise ImageFinderMethodError

        return (hkeypoints, hdescriptors, nkeypoints, ndescriptors)

    def _match_features(self, hkeypoints, hdescriptors,
                        nkeypoints, ndescriptors, similarity, match):
        if match == "in-house":
            # match the number of keypoints to their descriptor vectors
            # if a flat descriptor list is returned (old OpenCV descriptors)
            # e.g. needle row 5 is a descriptor vector for needle keypoint 5
            rowsize = len(hdescriptors) / len(hkeypoints)
            if rowsize > 1:
                hrows = numpy.array(hdescriptors, dtype = numpy.float32).reshape((-1, rowsize))
                nrows = numpy.array(ndescriptors, dtype = numpy.float32).reshape((-1, rowsize))
                #print hrows.shape, nrows.shape
            else:
                hrows = numpy.array(hdescriptors, dtype = numpy.float32)
                nrows = numpy.array(ndescriptors, dtype = numpy.float32)
                rowsize = len(hrows[0])

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
                descriptor = numpy.array(descriptor, dtype = numpy.float32).reshape((1, rowsize))
                #print i, descriptor.shape, samples[0].shape
                retval, results, neigh_resp, dists = knn.find_nearest(descriptor, 1)
                res, dist =  int(results[0][0]), dists[0][0]
                #print res, dist

                if dist <= 1.0 - similarity:
                    match_hkeypoints.append(hkeypoints[res])
                    match_nkeypoints.append(nkeypoints[i])
                else:
                    pass
                    #print "no", dist
            return (match_hkeypoints, hkeypoints, match_nkeypoints, nkeypoints)

        # include only methods tested for compatibility
        elif match in self.feature_matchers:
            matcher = cv2.DescriptorMatcher_create(match)
            # build matcher and match feature vectors
            matches = matcher.match(ndescriptors, hdescriptors)

            # then extract matches above some similarity as done below
            match_hkeypoints = []
            match_nkeypoints = []
            for match in matches:
                #print match.distance
                if match.distance <= 100.0 - 100 * similarity:
                    match_hkeypoints.append(hkeypoints[match.trainIdx])
                    match_nkeypoints.append(nkeypoints[match.queryIdx])

            return (match_hkeypoints, hkeypoints, match_nkeypoints, nkeypoints)

        else:
            raise ImageFinderMethodError

    def _get_opencv_images(self, haystack, needle, gray = False):
        opencv_haystack = numpy.array(haystack.get_pil_image())
        # convert RGB to BGR
        opencv_haystack = opencv_haystack[:, :, ::-1].copy()
 
        opencv_needle = numpy.array(needle.get_pil_image())
        # convert RGB to BGR
        opencv_needle = opencv_needle[:, :, ::-1].copy()

        if gray:
            opencv_haystack = cv2.cvtColor(opencv_haystack, cv2.COLOR_BGR2GRAY)
            opencv_needle = cv2.cvtColor(opencv_needle, cv2.COLOR_BGR2GRAY)

        return (opencv_haystack, opencv_needle)

    def _match_template(self, haystack, needle, nocolor, match):
        # Sanity check: Needle size must be smaller than haystack
        if haystack.get_width() < needle.get_width() or haystack.get_height() < needle.get_height():
            logging.warning("The size of the searched image is smaller than its region")
            return None

        methods = {"sqdiff" : cv2.TM_SQDIFF, "sqdiff_normed" : cv2.TM_SQDIFF_NORMED,
                   "ccorr" : cv2.TM_CCORR, "ccorr_normed" : cv2.TM_CCORR_NORMED,
                   "ccoeff" : cv2.TM_CCOEFF, "ccoeff_normed" : cv2.TM_CCOEFF_NORMED}
        if match not in methods.keys():
            raise ImageFinderMethodError

        if nocolor:
            gray_haystack, gray_needle = self._get_opencv_images(haystack, needle, gray = True)
            match = cv2.matchTemplate(gray_haystack, gray_needle, methods[match])
        else:
            opencv_haystack, opencv_needle = self._get_opencv_images(haystack, needle, gray = False)
            match = cv2.matchTemplate(opencv_haystack, opencv_needle, methods[match])

        # print a hotmap of the results for debugging purposes
        if self.image_logging:
            # currenly the image showing methods still don't work
            # due to opencv bug
            #cv2.startWindowThread()
            #cv2.namedWindow("test", 1)
            #cv2.imshow("test", match)

            hotmap = cv.CreateMat(len(match), len(match[0]), cv.CV_8UC1)
            cv.ConvertScale(cv.fromarray(match), hotmap, scale = 255.0)
            hotmap = numpy.asarray(hotmap)
            cv2.imwrite("last_hotmap.png", hotmap)

        return match

