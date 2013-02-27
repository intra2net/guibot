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
    through autopy or through the OpenCV library. The image finding
    methods include: general find, template and feature find, and
    all matches above similarity find.
    """

    def __init__(self, equalizer = None):
        """
        Initiates the image finder and its CV backend equalizer.

        The image logging consists of saving the last hotmap. If the
        template matching method was used, the hotmap is a finger
        print of the matching in the entire haystack. Its lighter
        areas are places where the needle was matched better. If the
        feature matching method was used, the hotmap contains the
        matched needle features in the haystack (green), the ones
        that were not matched (red), and the calculated focus point
        that would be used for clicking, hovering, etc. (blue).
        """
        if equalizer == None:
            self.eq = CVEqualizer()
        else:
            self.eq = equalizer

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
        if self.eq.current["find"] == "template":
            return self.find_template(haystack, needle, similarity, nocolor)
        elif self.eq.current["find"] == "feature":
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
        if self.eq.current["tmatch"] not in self.eq.algorithms["template_matchers"]:
            raise ImageFinderMethodError

        elif self.eq.current["tmatch"] == "autopy":
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
            result = self._match_template(haystack, needle, nocolor, self.eq.current["tmatch"])

            minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(result)
            logging.debug('minVal: %s', str(minVal))
            logging.debug('minLoc: %s', str(minLoc))
            logging.debug('maxVal (similarity): %s (%s)',
                          str(maxVal), similarity)
            logging.debug('maxLoc (x,y): %s', str(maxLoc))
            # switch max and min for sqdiff and sqdiff_normed
            if self.eq.current["tmatch"] in ("sqdiff", "sqdiff_normed"):
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
        Available parameters are: oldSURFdetect, ratioThreshold, ransacReprojThreshold
        """
        self.hotmap[0], _ = self._get_opencv_images(haystack, needle)
        self.hotmap[1] = 0.0
        self.hotmap[2] = None

        # grayscale images have features of better invariance and therefore
        # are the type of images used in computer vision
        hkp, hdc, nkp, ndc = self._detect_features(haystack, needle,
                                                   self.eq.current["fdetect"],
                                                   self.eq.current["fextract"])
        # check for quality of the detected features
        if len(nkp) < 4 or len(hkp) < 4:
            if self.image_logging <= 10:
                cv2.imwrite("log.png", self.hotmap[0])
            return None

        mhkp, mnkp = self._match_features(hkp, hdc, nkp, ndc,
                                          self.eq.current["fmatch"])

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
                                     numpy.array([kp.pt for kp in mhkp]), cv2.RANSAC,
                                     self.eq.parameters["find"]["ransacReprojThreshold"])
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
        if self.eq.current["tmatch"] not in self.eq.algorithms["template_matchers"]:
            raise ImageFinderMethodError

        # autopy template matching for find_all is replaced by ccoeff_normed
        # since it is inefficient and returns match clouds
        if self.eq.current["tmatch"] == "autopy":
            match_template = "ccoeff_normed"
        else:
            match_template = self.eq.current["tmatch"]
        result = self._match_template(haystack, needle, nocolor, match_template)

        # extract maxima once for each needle size region
        maxima = []
        while True:

            minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(result)
            # switch max and min for sqdiff and sqdiff_normed
            if self.eq.current["tmatch"] in ("sqdiff", "sqdiff_normed"):
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
                hessian_threshold = self.eq.parameters["fdetect"]["oldSURFdetect"]
                detector = cv2.SURF(hessian_threshold)

                (hkeypoints, hdescriptors) = detector.detect(hgray, None, useProvidedKeypoints = False)
                (nkeypoints, ndescriptors) = detector.detect(ngray, None, useProvidedKeypoints = False)

            # include only methods tested for compatibility
            elif (detect in self.eq.algorithms["feature_detectors"]
                  and extract in self.eq.algorithms["feature_extractors"]):
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
        def ratio_test(matches):
            """
            The ratio test checks the first and second best match. If their
            ratio is close to 1.0, there are both good candidates for the
            match and the probabilty of error when choosing one is greater.
            Therefore these matches are ignored and thus only matches of
            greater probabilty are returned.
            """
            matches2 = []
            for m in matches:

                if len(m) > 1:
                    # smooth to make 0/0 case also defined as 1.0
                    smooth_dist1 = m[0].distance + 0.0000001
                    smooth_dist2 = m[1].distance + 0.0000001

                    #print smooth_dist1 / smooth_dist2, self.ratio
                    if (smooth_dist1 / smooth_dist2 < self.eq.parameters["fmatch"]["ratioThreshold"]):
                        matches2.append(m[0])
                else:
                    matches2.append(m[0])

            #print "rt: %i\%i" % (len(matches2), len(matches))
            return matches2

        def symmetry_test(nmatches, hmatches):
            """
            Refines the matches with a symmetry test which extracts
            only the matches in agreement with both the haystack and needle
            sets of keypoints. The two keypoints must be best feature
            matching of each other to ensure the error by accepting the
            match is not too large.
            """
            matches2 = []
            for nm in nmatches:
                for hm in hmatches:

                    if nm.queryIdx == hm.trainIdx and nm.trainIdx == hm.queryIdx:
                        m = cv2.DMatch(nm.queryIdx, nm.trainIdx, nm.distance)
                        matches2.append(m)
                        break

            #print "st: %i\%i" % (len(matches2), len(matches))
            return matches2

        if match == "in-house":
            matcher = InHouseCV()

            # NOTE: the method below should currently be uncommented
            # only for testing
            #matcher.contextMatch(ndescriptors, hdescriptors,
            #                     nkeypoints, hkeypoints)

        # include only methods tested for compatibility
        elif match in self.eq.algorithms["feature_matchers"]:
            # build matcher and match feature vectors
            matcher = cv2.DescriptorMatcher_create(match)
        else:
            raise ImageFinderMethodError

        # find and filter matches through tests
        if self.eq.parameters["fmatch"]["ratioTest"]:
            matches = matcher.knnMatch(ndescriptors, hdescriptors, 2)
            matches = ratio_test(matches)
        else:
            matches = matcher.knnMatch(ndescriptors, hdescriptors, 1)
            matches = [m[0] for m in matches]
        if self.eq.parameters["fmatch"]["symmetryTest"]:
            if self.eq.parameters["fmatch"]["ratioTest"]:
                hmatches = matcher.knnMatch(hdescriptors, ndescriptors, 2)
                hmatches = ratio_test(hmatches)
            else:
                hmatches = matcher.knnMatch(hdescriptors, ndescriptors, 1)
                hmatches = [hm[0] for hm in hmatches]
            matches = symmetry_test(matches, hmatches)

        # prepare final matches
        match_hkeypoints = []
        match_nkeypoints = []
        matches = sorted(matches, key = lambda x: x.distance)
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


class CVEqualizer:
    def __init__(self):
        """
        Initiates the CV equalizer with default algorithm configuration.

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

        Available parameters:
            detect filter - works for certain detectors and
                determines how many initial features are
                detected in an image (e.g. hessian threshold for
                SURF detector)
            match filter - determines what part of all matches
                returned by feature matcher remain good matches
            project filter - determines what part of the good
                matches are considered inliers
            ratio test - boolean for whether to perform a ratio test
            symmetry test - boolean for whether to perform a symmetry test
        """
        # currently fully compatible methods
        self.algorithms = {"find_methods" : ("template", "feature"),
                           "template_matchers" : ("autopy", "sqdiff", "ccorr",
                                                  "ccoeff", "sqdiff_normed",
                                                  "ccorr_normed", "ccoeff_normed"),
                           "feature_matchers" : ("BruteForce", "BruteForce-L1",
                                                 "BruteForce-Hamming",
                                                 "BruteForce-Hamming(2)", "in-house"),
                           "feature_detectors" : ("ORB", "oldSURF"),
                           "feature_extractors" : ("ORB", "BRIEF", "FREAK")}

        # default parameters
        self.parameters = {"find" : {"ransacReprojThreshold" : 10.0},
                           "tmatch" : {}, "fdetect" : {}, "fextract" : {},
                           "fmatch" : {"ratioThreshold" : 0.65,
                                       "ratioTest" : False,
                                       "symmetryTest" : False}}

        # default algorithms
        self.current = {"find" : "template",
                        "tmatch" : "ccoeff_normed",
                        "fdetect" : "ORB",
                        "fextract" : "BRIEF",
                        "fmatch" : "BruteForce-Hamming"}
        self.configure_backend(find_image = self.current["find"],
                               template_match = self.current["tmatch"],
                               feature_detect = self.current["fdetect"],
                               feature_extract = self.current["fextract"],
                               feature_match = self.current["fmatch"])

    def configure_backend(self, find_image = None, template_match = None,
                          feature_detect = None, feature_extract = None,
                          feature_match = None):
        """
        Change some or all of the algorithms used as backend for the
        image finder.
        """
        if find_image != None:
            if find_image not in self.algorithms["find_methods"]:
                raise ImageFinderMethodError
            else:
                self._replace_params("find", self.current["find"],
                                    find_image)
                self.current["find"] = find_image
        if template_match != None:
            if template_match not in self.algorithms["template_matchers"]:
                raise ImageFinderMethodError
            else:
                self._replace_params("tmatch", self.current["tmatch"],
                                    template_match)
                self.current["tmatch"] = template_match
        if feature_detect != None:
            if feature_detect not in self.algorithms["feature_detectors"]:
                raise ImageFinderMethodError
            else:
                self._replace_params("fdetect", self.current["fdetect"],
                                    feature_detect)
                self.current["fdetect"] = feature_detect
        if feature_extract != None:
            if feature_extract not in self.algorithms["feature_extractors"]:
                raise ImageFinderMethodError
            else:
                self._replace_params("fextract", self.current["fextract"],
                                    feature_extract)
                self.current["fextract"] = feature_extract
        if feature_match != None:
            if feature_match not in self.algorithms["feature_matchers"]:
                raise ImageFinderMethodError
            else:
                self._replace_params("fmatch", self.current["fmatch"],
                                    feature_match)
                self.current["fmatch"] = feature_match

    def _replace_params(self, category, curr_old, curr_new):
        """Update the parameters dictionary according to a new backend algorithm."""
        if category == "find":
            return
        elif category == "tmatch":
            return
        elif category == "fdetect":
            if curr_new == "oldSURF":
                self.parameters[category]["oldSURFdetect"] = 85
            else:
                old_backend = cv2.FeatureDetector_create(curr_old)
                new_backend = cv2.FeatureDetector_create(curr_new)
        elif category == "fextract":
            old_backend = cv2.DescriptorExtractor_create(curr_old)
            new_backend = cv2.DescriptorExtractor_create(curr_new)
        elif category == "fmatch":
            if curr_new != "in-house":
                # BUG: a bug of OpenCV leads to crash if parameters
                # are extracted from the matcher interface although
                # the API supports it
                return
                old_backend = cv2.DescriptorMatcher_create(curr_old)
                new_backend = cv2.DescriptorMatcher_create(curr_new)

        # examine the interface of the OpenCV backend
        #print old_backend, dir(old_backend)
        #print new_backend, dir(new_backend)
        for param in old_backend.getParams():
            if self.parameters[category].has_key(param):
                self.parameters[category].pop(param)
        for param in new_backend.getParams():
            #print new_backend.paramHelp(param)
            ptype = new_backend.paramType(param)
            if ptype == 0:
                val = new_backend.getInt(param)
            elif ptype == 1:
                val = new_backend.getBool(param)
            elif ptype == 2:
                val = new_backend.getDouble(param)
            else:
                # designed to raise error so that the other ptypes are identified
                # currently unknown indices: getMat, getAlgorithm, getMatVector, getString
                #print param, ptype
                val = new_backend.getAlgorithm(param)
            self.parameters[category][param] = val
            #print param, "=", val
        #print self.parameters[category], "\n"


class InHouseCV:
    """
    ImageFinder backend with in-house CV algorithms.
    """

    def __init__(self):
        """Initiate thee CV backend attributes."""
        self.detector = cv2.FeatureDetector_create("ORB")
        self.extractor = cv2.DescriptorExtractor_create("ORB")

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

    def regionMatch(self, desc1, desc2, kp1, kp2):
        """
        Use location information to better decide on matched features.

        TODO: Implement this method.
        """
        def ncoord(match):
            return kp1[match.queryIdx].pt
        def hcoord(match):
            return kp2[match.trainIdx].pt
        def match_quadrant():
            pass

        matches = self.knnMatch(desc1, desc2, 100, 1, 0.5)
        for m in matches:
            print len(m), ncoord(m[0]), hcoord(m[0])

        return matches

    def knnMatch(self, desc1, desc2, k = 1, desc4kp = 1, autostop = 0.0):
        """
        In-house feature matching algorithm taking needle and haystack
        keypoints and their descriptors and returning a list of DMatch
        tuples (first and second best match).

        Performs k-Nearest Neighbor matching.

        @param desc1, desc1: descriptors of the matched images
        @param k: categorization up to k-th nearest neighbor
        @param desc4kp: legacy parameter for the old SURF() feature detector
        where desc4kp = len(desc2) / len(kp2) or analogically len(desc1) / len(kp1)
        i.e. needle row 5 is a descriptor vector for needle keypoint 5
        @param autostop: stop automatically if the ratio (dist to k)/(dist to k+1)
        is close to 0, i.e. the k+1-th neighbor is too far.
        """
        if desc4kp > 1:
            desc1 = numpy.array(desc1, dtype = numpy.float32).reshape((-1, desc4kp))
            desc2 = numpy.array(desc2, dtype = numpy.float32).reshape((-1, desc4kp))
            #print desc1.shape, desc2.shape
        else:
            desc1 = numpy.array(desc1, dtype = numpy.float32)
            desc2 = numpy.array(desc2, dtype = numpy.float32)
        desc_size = desc2.shape[1]

        # kNN training - learn mapping from rows2 to kp2 index
        samples = desc2
        responses = numpy.arange(int(len(desc2)/desc4kp), dtype = numpy.float32)
        #print len(samples), len(responses)
        knn = cv2.KNearest()
        knn.train(samples, responses)

        matches = []
        # retrieve index and value through enumeration
        for i, descriptor in enumerate(desc1):
            descriptor = numpy.array(descriptor, dtype = numpy.float32).reshape((1, desc_size))
            #print i, descriptor.shape, samples[0].shape
            kmatches = []
            ratio = 1.0

            for ki in range(k):
                _, res, _, dists = knn.find_nearest(descriptor, ki+1)
                #print res, dists

                if len(dists[0]) > 1 and autostop > 0.0:

                    # smooth to make 0/0 case also defined as 1.0
                    dist1 = dists[0][-2] + 0.0000001
                    dist2 = dists[0][-1] + 0.0000001
                    ratio = dist1 / dist2
                    #print ratio, autostop
                    if ratio > autostop:
                        break

                kmatches.append(cv2.DMatch(i, int(res[0][0]), dists[0][-1]))

            matches.append(tuple(kmatches))
        return matches
