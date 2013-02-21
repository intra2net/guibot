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
    """
    The image finder contains all image matching functionality.

    It offers both template matching and feature matching algorithms
    through autopy or through the OpenCV library. Besides the image
    finding methods (general find, template and feature find, and
    find all matches above similarity), it provides with a second
    group of methods to facilitate and automate the selection of
    algorithms and parameters that are most successful for a custom
    image (benchmarking and calibration methods).
    """

    def __init__(self):
        """
        Initiates the image finder with default algorithm configuration.

        Available algorithms:
            template matchers:
                autopy, sqdiff, ccorr, ccoeff
                sqdiff_normed, *ccorr_normed, ccoeff_normed

            feature detectors:
                *FAST, *STAR, *SIFT, *SURF, ORB, *MSER,
                *GFTT, *HARRIS, *Dense, *SimpleBlob
                *GridFAST, *GridSTAR, ...
                *PyramidFAST, *PyramidSTAR, ...
                *oldSURF (OpenCV 2.2.3)

            feature extractors:
                *SIFT, *SURF, ORB, BRIEF, FREAK

            feature matchers:
                BruteForce, BruteForce-L1, BruteForce-Hamming,
                BruteForce-Hamming(2), **FlannBased, in-house

            Starred methods are currently known to be buggy.
            Double starred methods should be investigated further.

        Available parameters (equalizer):
            detect filter - works for certain detectors and
                determines how many initial features are
                detected in an image (e.g. hessian threshold for
                SURF detector)
            match filter - determines what part of all matches
                returned by feature matcher remain good matches
            project filter - determines what part of the good
                matches are considered inliers

        Image logging:
            The image logging consists of saving the last hotmap. If the
            template matching method was used, the hotmap is a finger
            print of the matching in the entire haystack. Its lighter
            areas are places where the needle was matched better. If the
            feature matching method was used, the hotmap contains the
            matched needle features in the haystack (green), the ones
            that were not matched (red), and the calculated focus point
            that would be used for clicking, hovering, etc. (blue).
        """
        # currently fully compatible methods
        self.find_methods = ("template", "features")
        self.template_matchers = ("autopy", "sqdiff", "ccorr", "ccoeff",
                                  "sqdiff_normed", "ccorr_normed", "ccoeff_normed")
        self.feature_matchers = ("BruteForce", "BruteForce-L1", "BruteForce-Hamming",
                                 "BruteForce-Hamming(2)", "in-house")
        self.feature_detectors = ("ORB", "oldSURF")
        self.feature_extractors = ("ORB", "BRIEF", "FREAK")

        # default algorithms
        self.find_image = "template"
        self.match_template = "ccoeff_normed"
        self.detect_features = "ORB"
        self.extract_features = "BRIEF"
        self.match_features = "BruteForce-Hamming"

        # default parameters
        self.equalizer = {"detect_filter" : 85,
                          "match_filter" : 1.0,
                          "project_filter" : 10.0}

        # other attributes
        self._bitmapcache = {}
        # 0 NOTSET, 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL
        self.image_logging = 20
        # contains the last matched image as a numpy array, the matched
        # similarity and the matched coordinates
        self.hotmap = [None, -1.0, None]

    def find(self, haystack, needle, similarity, nocolor = True):
        """
        Finds an image in another if above some similarity and returns a
        Location() object or None using all default algorithms and parameters.

        This is the most general find method.

        @param haystack: an Image() to look in
        @param needle: an Image() to look for
        @param similarity: a float in the interval [0.0, 1.0] where 1.0
        requires 100% match
        @param nocolor: a bool defining whether to use grayscale images
        """
        if self.find_image == "template":
            return self.find_template(haystack, needle, similarity, nocolor)
        elif self.find_image == "features":
            return self.find_features(haystack, needle, similarity)
        else:
            raise ImageFinderMethodError

    def find_template(self, haystack, needle, similarity, nocolor = True):
        """
        Finds a needle image in a haystack image using template matching.

        Returns a Location object for the match or None in not found.

        Available template matching methods are: autopy, opencv
        Available parameters are: None
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
                coord = autopy_screenshot.find_bitmap(autopy_needle, autopy_tolerance)

                if coord is not None:
                    self.hotmap[1] = -1.0
                    self.hotmap[2] = coord
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
            # switch max and min for sqdiff and sqdiff_normed
            if self.match_template in ("sqdiff", "sqdiff_normed"):
                maxVal = 1 - minVal
                maxLoc = minLoc

            # print a hotmap of the results for debugging purposes
            if self.image_logging <= 20:
                # currenly the image showing methods still don't work
                # due to opencv bug
                #cv2.startWindowThread()
                #cv2.namedWindow("test", 1)
                #cv2.imshow("test", match)

                hotmap = cv.CreateMat(len(result), len(result[0]), cv.CV_8UC1)
                cv.ConvertScale(cv.fromarray(result), hotmap, scale = 255.0)
                self.hotmap[0] = numpy.asarray(hotmap)
                cv2.imwrite("log.png", self.hotmap[0])

            if maxVal > similarity:
                self.hotmap[1] = maxVal
                self.hotmap[2] = maxLoc
                return Location(maxLoc[0], maxLoc[1])
            return None

    def find_features(self, haystack, needle, similarity):
        """
        Finds a needle image in a haystack image using feature matching.

        Returns a Location object for the match or None in not found.

        Available methods are: a combination of feature detector,
        extractor, and matcher
        Available parameters are: detect_filter, match_filter, project_filter
        """
        self.hotmap[0], _ = self._get_opencv_images(haystack, needle)
        self.hotmap[1] = 0.0
        self.hotmap[2] = None

        # grayscale images have features of better invariance and therefore
        # are the type of images used in computer vision
        hkp, hdc, nkp, ndc = self._detect_features(haystack, needle,
                                                   detect = self.detect_features,
                                                   extract = self.extract_features)
        # check for quality of the detected features
        if len(nkp) < 4 or len(hkp) < 4:
            if self.image_logging <= 10:
                cv2.imwrite("log.png", self.hotmap[0])
            return None

        mhkp, mnkp = self._match_features(hkp, hdc, nkp, ndc, self.match_features)

        # plot the detected and matched features for image logging
        if self.image_logging <= 10:
            for kp in hkp:
                if kp in mhkp:
                    # these matches are half the way to being good
                    color = (0, 255, 255)
                else:
                    color = (0, 0, 255)
                x, y = kp.pt
                cv2.circle(self.hotmap[0], (int(x),int(y)), 2, color, -1)

        # check for quality of the match
        s = float(len(mnkp)) / float(len(nkp))
        #print "%s\\%s" % (len(mhkp), len(hkp)), "%s\\%s" % (len(mnkp), len(nkp)), "-> %f" % s
        if s < similarity or len(mnkp) < 4:
            if self.image_logging <= 10:
                cv2.imwrite("log.png", self.hotmap[0])
            return None

        # calculate needle projection using random sample consensus
        # homography and fundamental matrix as options - homography is considered only
        # for rotation but currently gives better results than the fundamental matrix
        H, mask = cv2.findHomography(numpy.array([kp.pt for kp in mnkp]),
                                     numpy.array([kp.pt for kp in mhkp]),
                                     cv2.RANSAC, self.equalizer["project_filter"])
        #H, mask = cv2.findFundamentalMat(numpy.array([kp.pt for kp in mnkp]),
        #                                 numpy.array([kp.pt for kp in mhkp]),
        #                                 method = cv2.RANSAC, param1 = 10.0,
        #                                 param2 = 0.9)
        (ocx, ocy) = (needle.get_width() / 2, needle.get_height() / 2)
        orig_center_wrapped = numpy.array([[[ocx, ocy]]], dtype = numpy.float32)
        #print orig_center_wrapped.shape, H.shape
        match_center_wrapped = cv2.perspectiveTransform(orig_center_wrapped, H)
        (mcx, mcy) = (match_center_wrapped[0][0][0], match_center_wrapped[0][0][1])

        # measure total used features for the projected focus point
        total_matches = 0
        for kp in mhkp:
            # true matches are also inliers for the homography
            if mask[mhkp.index(kp)][0] == 1:
                total_matches += 1
                # plot the correctly projected features
                if self.image_logging <= 10:
                    color = (0, 255, 0)
                    x, y = kp.pt
                    cv2.circle(self.hotmap[0], (int(x),int(y)), 2, color, -1)

        # plot the focus point used for clicking and other operations
        if self.image_logging <= 20:
            cv2.circle(self.hotmap[0], (int(mcx),int(mcy)), 4, (255,0,0), -1)
            cv2.imwrite("log.png", self.hotmap[0])
        self.hotmap[1] = float(total_matches) / float(len(mnkp))
        self.hotmap[2] = (mcx, mcy)

        # check for quality of the projection
        s = float(total_matches) / float(len(mnkp))
        #print "%s\\%s" % (total_matches, len(mnkp)), "-> %f" % s, "<?", similarity
        if s < similarity:
            return None
        else:
            return Location(int(mcx), int(mcy))

    def find_all(self, haystack, needle, similarity, nocolor = True):
        """
        Finds all needle images in a haystack image using template matching.

        Returns a list of Location objects for all matches or None in not found.

        Available template matching methods are: opencv
        Available parameters are: None
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
            # switch max and min for sqdiff and sqdiff_normed
            if self.match_template in ("sqdiff", "sqdiff_normed"):
                # TODO: check whetehr find_all would work properly for sqdiff
                maxVal = 1 - minVal
                maxLoc = minLoc
            if maxVal < similarity:
                break

            logging.debug('Found a match with:')
            logging.debug('maxVal (similarity): %s (%s)',
                          str(maxVal), similarity)
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

        # print a hotmap of the results for debugging purposes
        if self.image_logging <= 20:
            hotmap = cv.CreateMat(len(result), len(result[0]), cv.CV_8UC1)
            cv.ConvertScale(cv.fromarray(result), hotmap, scale = 255.0)
            self.hotmap[0] = numpy.asarray(hotmap)
            cv2.imwrite("log.png", self.hotmap[0])
        self.hotmap[1] = maxVal
        self.hotmap[2] = maxLoc

        return maxima

    def benchmark_find(self, haystack, needle, calibration = True,
                       tolerance = 0.1, refinements = 50):
        """
        Performs benchmarking on all available algorithms and returns a list of
        (method, success, coordinates) tuples sorted according to similarity (success).

        Use this method to choose the best algorithm to find your specific image
        (or image category). Use the "calibrate" method to find the best parameters
        if you have already chosen the algorithm.

        Note: This method already uses calibrate internally to provide the best
        outcome for each compared method (optimal success). You will not gain
        the same result if you don't calibrate the parameters. To turn the calibration
        off and benchmark with your selected parameters, change the "calibration"
        function argument.

        Note: Methods that are supported by OpenCV but currently don't work are
        excluded from the dictionary. The dictionary can thus also be used
        to assess what are the available and working methods besides their success
        for a given needle and haystack.

        @param calibration: whether to use calibration
        @param tolerance: tolerable deviation for all parameters
        @param refinements: number of refinements allowed to improve calibration
        """
        results = []

        # test all template matching methods
        old_config = (self.match_template)
        for key in self.template_matchers:
            # autopy does not provide any similarity value
            # and only normed methods are comparable
            if "_normed" not in key:
                continue

            for gray in (True, False):
                if gray:
                    method = key + "_gray"
                else:
                    method = key
                self.match_template = key
                self.find_template(haystack, needle, 0.0, gray)
                #print "%s,%s,%s,%s" % (needle.filename, method, self.hotmap[1], self.hotmap[2])
                results.append((method, self.hotmap[1], self.hotmap[2]))
        self.match_template = old_config[0]

        # test all feature matching methods
        old_config = (self.detect_features,
                      self.extract_features,
                      self.match_features)
        for key_fd in self.feature_detectors:
            # skip in-house because of opencv version bug
            if key_fd == "oldSURF":
                continue
            for key_fe in self.feature_extractors:
                for key_fm in self.feature_matchers:
                    self.detect_features = key_fd
                    self.extract_features = key_fe
                    self.match_features = key_fm
                    if calibration:
                        self.calibrate_find(haystack, needle, tolerance, refinements)
                    else:
                        self.find_features(haystack, needle, 0.0)
                    method = "%s-%s-%s" % (key_fd, key_fe, key_fm)
                    #print "%s,%s,%s,%s" % (needle.filename, method, self.hotmap[1], self.hotmap[2])
                    results.append((method, self.hotmap[1], self.hotmap[2]))
        self.detect_features = old_config[0]
        self.extract_features = old_config[1]
        self.match_features = old_config[2]
        return sorted(results, key = lambda x: x[1], reverse = True)

    def calibrate_find(self, haystack, needle, tolerance = 0.1, refinements = 50):
        """
        Calibrates the available parameters (the equalizer) for a given
        needle and haystack.

        Returns the minimized error (in terms of similarity) for the given
        number of refinements and tolerated best parameter range.
        """
        def run(params):
            """
            Internal custom function to evaluate error for a given set of parameters.
            """
            self.equalizer["detect_filter"] = params[0]
            self.equalizer["match_filter"] = params[1]
            self.equalizer["project_filter"] = params[2]

            self.find_features(haystack, needle, 0.0)
            error = 1.0 - self.hotmap[1]
            return error

        def twiddle(full_params, run_function, tolerance, max_attempts):
            """
            Function to optimize a set of parameters for a minimal returned error.

            @param parameters: a list of parameter triples of the form (min, start, max)
            @param run_function: a function that accepts a list of tested parameters
            and returns the error that should be minimized
            @param tolerance: minimal parameter delta (uncertainty interval)
            @param max_attempts: maximal number of refinements to reach the parameter
            delta below the tolerance.

            Special credits for this approach should be given to Prof. Sebastian Thrun,
            who explained it in his Artificial Intelligence for Robotics class.
            """
            params = [p[1] for p in full_params]
            # the min and max will be checked first with such deltas
            deltas = [(abs(p[2]-p[0])) for p in full_params]

            best_params = params
            best_error = run_function(params)
            #print best_params, best_error

            n = 0
            while sum(deltas) > tolerance and n < max_attempts and best_error > 0.0:
                for i in range(len(params)):
                    curr_param = params[i]

                    params[i] = min(curr_param + deltas[i], full_params[i][2])
                    error = run_function(params)
                    if(error < best_error):
                        best_params = params
                        best_error = error
                        deltas[i] *= 1.1
                    else:

                        params[i] = max(curr_param - deltas[i], full_params[i][0])
                        error = run_function(params)
                        if(error < best_error):
                            best_params = params
                            best_error = error
                            deltas[i] *= 1.1
                        else:
                            params[i] = curr_param
                            deltas[i] *= 0.9
                #print best_params, best_error
                n += 1

            return (best_params, best_error)

        full_params = []
        full_params.append((0.0, self.equalizer["detect_filter"], 200.0))
        full_params.append((0.0, self.equalizer["match_filter"], 1.0))
        full_params.append((0.0, self.equalizer["project_filter"], 200.0))

        best_params, error = twiddle(full_params, run, tolerance, refinements)
        #print best_params, error

        self.equalizer["detect_filter"] = best_params[0]
        self.equalizer["match_filter"] = best_params[1]
        self.equalizer["project_filter"] = best_params[2]

        return error

    def _detect_features(self, haystack, needle, detect, extract):
        """
        Detect all keypoints and calculate their respective decriptors.

        Perform zooming in the picture if the number of detected features
        is too low to project later on.
        """
        hgray, ngray = self._get_opencv_images(haystack, needle, gray = True)
        hkeypoints, nkeypoints = [], []
        hfactor, nfactor = 1, 1
        i, maxzoom = 0, 5

        # minimum 4 features are required for calculating the homography matrix
        while len(hkeypoints) < 4 or len(nkeypoints) < 4 and i < maxzoom:
            i += 1

            if detect == "oldSURF":
                # build the old surf feature detector
                hessian_threshold = self.equalizer["detect_filter"]
                detector = cv2.SURF(hessian_threshold)

                (hkeypoints, hdescriptors) = detector.detect(hgray, None, useProvidedKeypoints = False)
                (nkeypoints, ndescriptors) = detector.detect(ngray, None, useProvidedKeypoints = False)

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

            # if less than minimum features, zoom in small images to detect more
            #print len(nkeypoints), len(hkeypoints)
            if len(nkeypoints) < 4:
                nmat = cv.fromarray(ngray)
                nmat_zoomed = cv.CreateMat(nmat.rows * 2, nmat.cols * 2, cv.CV_8UC1)
                nfactor *= 2
                logging.debug("Minimum 4 features are required while only %s from needle "\
                              "were detected - zooming x%i needle to increase them!",
                              len(nkeypoints), nfactor)
                #print nmat.rows, nmat.cols
                cv.Resize(nmat, nmat_zoomed)
                ngray = numpy.asarray(nmat_zoomed)
            if len(hkeypoints) < 4:
                hmat = cv.fromarray(hgray)
                hmat_zoomed = cv.CreateMat(hmat.rows * 2, hmat.cols * 2, cv.CV_8UC1)
                hfactor *= 2
                logging.debug("Minimum 4 features are required while only %s from haystack "\
                                "were detected - zooming x%i haystack to increase them!",
                                len(hkeypoints), hfactor)
                #print hmat.rows, hmat.cols
                cv.Resize(hmat, hmat_zoomed)
                hgray = numpy.asarray(hmat_zoomed)

        # reduce keypoint coordinates to the original image size
        for hkeypoint in hkeypoints:
            hkeypoint.pt = (hkeypoint.pt[0] / hfactor, hkeypoint.pt[1] / hfactor)
        for nkeypoint in nkeypoints:
            nkeypoint.pt = (nkeypoint.pt[0] / nfactor, nkeypoint.pt[1] / nfactor)

        return (hkeypoints, hdescriptors, nkeypoints, ndescriptors)

    def _match_features(self, hkeypoints, hdescriptors,
                        nkeypoints, ndescriptors, match):
        """
        Match two sets of keypoints based on their descriptors.
        """
        if match == "in-house":
            matcher = InHouseCV()
            matches = matcher.match_features(hkeypoints, hdescriptors,
                                             nkeypoints, ndescriptors)

        # include only methods tested for compatibility
        elif match in self.feature_matchers:
            matcher = cv2.DescriptorMatcher_create(match)
            # build matcher and match feature vectors
            matches = matcher.match(ndescriptors, hdescriptors)

        else:
            raise ImageFinderMethodError

        # then extract matches above some similarity as done below
        match_hkeypoints = []
        match_nkeypoints = []
        matches = sorted(matches, key = lambda x: x.distance)
        max_nkp = self.equalizer["match_filter"] * len(nkeypoints)
        max_matches = min(int(max_nkp), len(matches))
        matches = matches[:max_matches]
        #print [m.distance for m in matches]
        for match in matches:
            #print match.distance
            match_hkeypoints.append(hkeypoints[match.trainIdx])
            match_nkeypoints.append(nkeypoints[match.queryIdx])

        return (match_hkeypoints, match_nkeypoints)

    def _get_opencv_images(self, haystack, needle, gray = False):
        """
        Convert the Image() objects into compatible numpy arrays.
        """
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
        """
        Match a color or grayscale needle image using the OpenCV
        template matching methods.
        """
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

        return match


class InHouseCV:
    """
    ImageFinder backend with in-house CV algorithms.
    """

    def __init__(self):
        pass

    def detect_features(self, haystack, needle):
        """
        In-house feature detect algorithm - currently not fully implemented!

        The current MSER might not be used in the actual implementation.
        """
        opencv_haystack, opencv_needle = self._get_opencv_images(haystack, needle)
        hgray, ngray = self._get_opencv_images(haystack, needle, gray = True)

        # TODO: this MSER blob feature detector is also available in
        # version 2.2.3 - implement if necessary
        detector = cv2.MSER()
        hregions = detector.detect(hgray, None)
        nregions = detector.detect(ngray, None)
        hhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in hregions]
        nhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in nregions]
        # show on final result
        cv2.polylines(opencv_haystack, hhulls, 1, (0, 255, 0))
        cv2.polylines(opencv_needle, nhulls, 1, (0, 255, 0))

        return None

    def match_features(self, hkp, hdesc, nkp, ndesc):
        """
        In-house feature matching algorithm taking needle and haystack
        keypoints and their descriptors and returning a list of DMatch
        objects.
        """
        # match the number of keypoints to their descriptor vectors
        # if a flat descriptor list is returned (old OpenCV descriptors)
        # e.g. needle row 5 is a descriptor vector for needle keypoint 5
        rowsize = len(hdesc) / len(hkp)
        if rowsize > 1:
            hrows = numpy.array(hdesc, dtype = numpy.float32).reshape((-1, rowsize))
            nrows = numpy.array(ndesc, dtype = numpy.float32).reshape((-1, rowsize))
            #print hrows.shape, nrows.shape
        else:
            hrows = numpy.array(hdesc, dtype = numpy.float32)
            nrows = numpy.array(ndesc, dtype = numpy.float32)
            rowsize = len(hrows[0])

        # kNN training - learn mapping from hrow to hkeypoints index
        samples = hrows
        responses = numpy.arange(len(hkp), dtype = numpy.float32)
        #print len(samples), len(responses)
        knn = cv2.KNearest()
        knn.train(samples,responses)

        matches = []
        # retrieve index and value through enumeration
        for i, descriptor in enumerate(nrows):
            descriptor = numpy.array(descriptor, dtype = numpy.float32).reshape((1, rowsize))
            #print i, descriptor.shape, samples[0].shape
            retval, results, neigh_resp, dists = knn.find_nearest(descriptor, 1)
            res, dist =  int(results[0][0]), dists[0][0]
            #print res, dist
            matches.append(cv2.DMatch(i, res, dist))

        return matches
