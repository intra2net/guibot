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
import PIL.Image

from settings import Settings, CVEqualizer
from location import Location
from imagelogger import ImageLogger
from errors import *

if Settings.find_image_backend() == "template" and Settings.template_match_backend() == "autopy":
    from autopy import bitmap
    from tempfile import NamedTemporaryFile
else:
    # TODO: OpenCV is required for 95% of the backends so we need to improve the image
    # logging and overall image manipulation in order to be able to truly avoid it
    import cv
    import cv2
    import math
    import numpy

import logging
log = logging.getLogger('guibender.imagefinder')


class ImageFinder:

    """
    The image finder contains all image matching functionality.

    It offers both template matching and feature matching algorithms
    through autopy or through the OpenCV library as well as a hybrid
    approach. The image finding methods include finding of one or
    all matches above the similarity defined as:

        self.eq.p["find"]["similarity"]

    There are many more parameters that could contribute for a good
    match in this "find" category or in other categories. They can
    all be manually adjusted or automatically calibrated.
    """

    def __init__(self, equalizer=None):
        """
        Initiates the image finder and its CV backend equalizer.

        The image logging consists of saving the last hotmap. If the
        template matching method was used, the hotmap is a finger
        print of the matching in the entire haystack. Its lighter
        areas are places where the needle was matched better. If the
        feature matching method was used, the hotmap contains the
        matched needle features in the haystack (green), the ones
        that were not matched (red), and the points in needle projected
        to the haystack that could be used for clicking, hovering,
        etc. (blue).
        """
        if equalizer == None:
            self.eq = CVEqualizer()
        else:
            self.eq = equalizer
        self.imglog = ImageLogger()

        # other attributes
        self._bitmapcache = {}

    def find(self, needle, haystack, multiple=False):
        """
        Finds an image in another and returns a Location() object
        or None using the backend algorithms and parameters
        defined in the "find" category.

        @param haystack: an Image() to look in
        @param needle: an Image() to look for
        @param multiple: retrieve all matches
        """
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        if needle.use_own_settings:
            log.debug("Using special needle settings for matching")
            general_settings = self.eq
            self.eq = needle.match_settings

        if self.eq.get_backend("find") == "template" and multiple:
            matches = self._template_find_all(needle, haystack)
        elif self.eq.get_backend("find") == "template":
            matches = self._template_find(needle, haystack)
        elif self.eq.get_backend("find") == "feature":
            matches = self._feature_find(needle, haystack)
        elif self.eq.get_backend("find") == "hybrid":
            matches = self._hybrid_find(needle, haystack, multiple)
        else:
            raise ImageFinderMethodError

        if needle.use_own_settings:
            self.eq = general_settings
        return matches

    def _template_find_all(self, needle, haystack):
        """
        Finds all needle images in a haystack image.

        The only available backend group for this is template matching.
        The only available template matching methods are: opencv

        Returns a list of Location objects for all matches or None in not found.
        """
        if self.eq.get_backend("tmatch") not in self.eq.algorithms["template_matchers"]:
            raise ImageFinderMethodError

        # autopy template matching for _template_find_all is replaced by ccoeff_normed
        # since it is inefficient and returns match clouds
        if self.eq.get_backend("tmatch") == "autopy":
            logging.warning("The backend algorithm autopy does not support "
                            "multiple matches on screen")
            match_template = "ccoeff_normed"
        else:
            match_template = self.eq.get_backend("tmatch")
        no_color = self.eq.p["find"]["nocolor"].value
        log.debug("Performing opencv-%s multiple template matching %s color",
                  match_template, "without" if no_color else "with")
        result = self._match_template(needle, haystack, no_color, match_template)
        if result is None:
            log.debug('_match_template() returned no result.')
            return []

        universal_hotmap = self.imglog.hotmap_from_template(result)

        # extract maxima once for each needle size region
        similarity = self.eq.p["find"]["similarity"].value
        maxima = []
        while True:

            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
            # switch max and min for sqdiff and sqdiff_normed
            if self.eq.get_backend("tmatch") in ("sqdiff", "sqdiff_normed"):
                # TODO: check whether _template_find_all would work propemultiple for sqdiff
                maxVal = 1 - minVal
                maxLoc = minLoc
            log.debug('Best match with value %s (similarity %s) and location (x,y) %s',
                      str(maxVal), similarity, str(maxLoc))

            if maxVal < similarity:
                if len(maxima) == 0:
                    self.imglog.similarities.append(maxVal)
                    self.imglog.locations.append(maxLoc)
                    self.imglog.hotmaps.append(universal_hotmap)
                log.debug("Best match is not accetable")
                break
            else:
                log.debug("Best match is accetable")
                self.imglog.similarities.append(maxVal)
                self.imglog.locations.append(maxLoc)
                self.imglog.hotmaps.append(universal_hotmap)
                maxima.append(Location(maxLoc[0], maxLoc[1]))

            res_w = haystack.width - needle.width + 1
            res_h = haystack.height - needle.height + 1
            match_x0 = max(maxLoc[0] - int(0.5 * needle.width), 0)
            match_x1 = min(maxLoc[0] + int(0.5 * needle.width), res_w)
            match_y0 = max(maxLoc[1] - int(0.5 * needle.height), 0)
            match_y1 = min(maxLoc[1] + int(0.5 * needle.height), len(result[0]))

            # log this only if performing deep internal debugging
            log.log(0, "Wipe image matches in x [%s, %s]/[%s, %s]",
                    match_x0, match_x1, 0, res_w)
            log.log(0, "Wipe image matches in y [%s, %s]/[%s, %s]",
                    match_y0, match_y1, 0, res_h)

            # clean found image to look for next safe distance match
            for i in range(max(maxLoc[0] - int(0.5 * needle.width), 0),
                           min(maxLoc[0] + int(0.5 * needle.width), res_w)):
                for j in range(max(maxLoc[1] - int(0.5 * needle.height), 0),
                               min(maxLoc[1] + int(0.5 * needle.height), res_h)):

                    log.log(0, "hw%s,hh%s - %s,%s,%s", haystack.width, needle.width, maxLoc[0],
                            maxLoc[0] - int(0.5 * needle.width), max(maxLoc[0] - int(0.5 * needle.width), 0))
                    log.log(0, "hw%s,nw%s - %s,%s,%s", haystack.width, needle.width, maxLoc[0],
                            maxLoc[0] + int(0.5 * needle.width), min(maxLoc[0] + int(0.5 * needle.width), 0))
                    log.log(0, "hh%s,nh%s - %s,%s,%s", haystack.height, needle.height, maxLoc[1],
                            maxLoc[1] - int(0.5 * needle.height), max(maxLoc[1] - int(0.5 * needle.height), 0))
                    log.log(0, "hh%s,nh%s - %s,%s,%s", haystack.height, needle.height, maxLoc[1],
                            maxLoc[1] + int(0.5 * needle.height), min(maxLoc[1] + int(0.5 * needle.height), 0))
                    log.log(0, "index at %s %s in %s %s", j, i, len(result), len(result[0]))

                    result[j][i] = 0.0
            log.log(0, "Total maxima up to the point are %i", len(maxima))
            log.log(0, "maxLoc was %s and is now %s", maxVal, result[maxLoc[1], maxLoc[0]])
        log.debug("A total of %i matches found", len(maxima))
        self.imglog.log(30, "template")

        return maxima

    def _template_find(self, needle, haystack):
        """
        Finds a needle image in a haystack image using template matching.

        Returns a Location object for the match or None in not found.

        Available template matching methods are: autopy, opencv
        """
        if self.eq.get_backend("tmatch") not in self.eq.algorithms["template_matchers"]:
            raise ImageFinderMethodError

        elif self.eq.get_backend("tmatch") == "autopy":
            # prepare a canvas solely for image logging
            self.imglog.hotmaps.append(haystack.preprocess())

            if needle.filename in self._bitmapcache:
                autopy_needle = self._bitmapcache[needle.filename]
            else:
                # load and cache it
                # TODO: Use in-memory conversion
                autopy_needle = bitmap.Bitmap.open(needle.filename)
                self._bitmapcache[needle.filename] = autopy_needle

            # TODO: Use in-memory conversion
            with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
                haystack.save(f.name)
                autopy_screenshot = bitmap.Bitmap.open(f.name)

                autopy_tolerance = 1.0 - self.eq.p["find"]["similarity"].value
                log.debug("Performing autopy template matching with tolerance %s (color)",
                          autopy_tolerance)
                # TODO: since only the coordinates are available
                # and fuzzy areas of matches are returned we need
                # to ask autopy team for returning the matching rates
                # as well
                coord = autopy_screenshot.find_bitmap(autopy_needle, autopy_tolerance)
                log.debug("Best acceptable match with location %s", coord)

                if coord is not None:
                    self.imglog.locations.append(coord)
                    self.imglog.log(30, "autopy")
                    return Location(coord[0], coord[1])
            self.imglog.log(30, "autopy")
            return None

        else:
            match_template = self.eq.get_backend("tmatch")
            no_color = self.eq.p["find"]["nocolor"].value
            similarity = self.eq.p["find"]["similarity"].value
            log.debug("Performing opencv-%s template matching %s color",
                      match_template, "without" if no_color else "with")
            result = self._match_template(needle, haystack, no_color, match_template)
            hotmap = self.imglog.hotmap_from_template(result)
            self.imglog.hotmaps.append(hotmap)

            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
            # switch max and min for sqdiff and sqdiff_normed
            if self.eq.get_backend("tmatch") in ("sqdiff", "sqdiff_normed"):
                maxVal = 1 - minVal
                maxLoc = minLoc
            # BUG: Due to an OpenCV bug sqdiff_normed might return a similarity > 1.0
            # although it must be normalized (i.e. between 0 and 1) so patch this and
            # other possible similar bugs
            maxVal = max(maxVal, 0.0)
            maxVal = min(maxVal, 1.0)
            log.debug('Best match with value %s (similarity %s) and location (x,y) %s',
                      str(maxVal), similarity, str(maxLoc))
            self.imglog.similarities.append(maxVal)
            self.imglog.locations.append(maxLoc)
            self.imglog.log(30, "template")

            acceptable = maxVal > similarity
            log.debug('Best match %s acceptable', "is" if acceptable else "is not")
            if acceptable:
                return Location(maxLoc[0], maxLoc[1])
            else:
                return None

    def _feature_find(self, needle, haystack):
        """
        Finds a needle image in a haystack image using feature matching.

        Returns a Location object for the match or None in not found.

        Available methods are: a combination of feature detector,
        extractor, and matcher
        """
        ngray = needle.preprocess(gray=True)
        hgray = haystack.preprocess(gray=True)
        hcanvas = haystack.preprocess(gray=False)

        # project more points for debugging purposes and image logging
        frame_points = []
        frame_points.append((needle.width / 2, needle.height / 2))
        frame_points.extend([(0, 0), (needle.width, 0), (0, needle.height),
                             (needle.width, needle.height)])

        similarity = self.eq.p["find"]["similarity"].value
        return self._project_features(frame_points, ngray, hgray,
                                      similarity, hcanvas)

    def _hybrid_find(self, needle, haystack, multiple=False):
        """
        Use template matching to deal with feature dense regions
        and guide a final feature matching.

        Feature matching is robust at small regions not too abundant
        of features where template matching is too picky. Template
        matching is good at large feature abundant regions and can be
        used as a heuristic for the feature matching.
        """
        # accumulate one template and multiple feature cases
        ImageLogger.accumulate_logging = True

        # use a different lower similarity for the template matching
        template_similarity = self.eq.p["find"]["front_similarity"].value
        feature_similarity = self.eq.p["find"]["similarity"].value
        log.debug("Using hybrid matching with template similarity %s "
                  "and feature similarity %s", template_similarity,
                  feature_similarity)

        self.eq.p["find"]["similarity"].value = template_similarity
        template_maxima = self._template_find_all(needle, haystack)

        self.eq.p["find"]["similarity"].value = feature_similarity
        ngray = needle.preprocess(gray=True)
        hgray = haystack.preprocess(gray=True)
        hcanvas = haystack.preprocess(gray=False)

        frame_points = []
        frame_points.append((needle.width / 2, needle.height / 2))
        frame_points.extend([(0, 0), (needle.width, 0), (0, needle.height),
                             (needle.width, needle.height)])

        feature_maxima = []
        is_feature_poor = False
        for upleft in template_maxima:
            up = upleft.get_y()
            down = min(haystack.height, up + needle.height)
            left = upleft.get_x()
            right = min(haystack.width, left + needle.width)
            log.log(0, "Maximum up-down is %s and left-right is %s",
                    (up, down), (left, right))

            haystack_region = hgray[up:down, left:right]
            haystack_region = haystack_region.copy()
            hotmap_region = hcanvas[up:down, left:right]
            hotmap_region = hotmap_region.copy()
            res = self._project_features(frame_points, ngray, haystack_region,
                                         feature_similarity, hotmap_region)
            if res != None:
                # take the template matching location rather than the feature one
                # for stability (they should ultimately be the same)
                #location = (left, up)
                location = (left + self.imglog.locations[-1][0],
                            up + self.imglog.locations[-1][1])
                self.imglog.locations[-1] = location

                feature_maxima.append([self.imglog.hotmaps[-1],
                                       self.imglog.similarities[-1],
                                       self.imglog.locations[-1]])
                # stitch back for a better final image logging
                hcanvas[up:down, left:right] = hotmap_region

            elif self.imglog.similarities[-1] == 0.0:
                is_feature_poor = True

        if is_feature_poor:
            log.warn("Feature poor needle detected, falling back to template matching")
            # NOTE: this has knowledge of the internal workings of the _template_find_all
            # template matching and more specifically that it orders the matches starting
            # with the best (this is ok, since this is also internal method)
            # NOTE: the needle can only be feature poor if there is at lease one
            # template matching
            feature_maxima = []
            for i, _ in enumerate(template_maxima):
                # test the template match also against the actual required similarity
                if self.imglog.similarities[i] > feature_similarity:
                    feature_maxima.append([self.imglog.hotmaps[i],
                                           self.imglog.similarities[i],
                                           self.imglog.locations[i]])

        # release the accumulated logging from subroutines
        ImageLogger.accumulate_logging = False
        if len(feature_maxima) == 0:
            log.debug("No acceptable match with the given feature similarity %s",
                      feature_similarity)
            # NOTE: handle cases when the matching failed at the feature stage, i.e. dump
            # a hotmap for debugging also in this case
            if len(self.imglog.similarities) > 1:
                self.imglog.hotmaps.append(hcanvas)
                self.imglog.similarities.append(self.imglog.similarities[len(template_maxima)])
                self.imglog.locations.append(self.imglog.locations[len(template_maxima)])
            self.imglog.log(30, "hybrid")
            if multiple:
                return []
            else:
                return None

        # NOTE: the best of all found will always be logged but if multiple matches
        # are allowed they will all be present on the dumped final canvas
        best_acceptable = max(feature_maxima, key=lambda x: x[1])
        self.imglog.hotmaps.append(hcanvas)
        self.imglog.similarities.append(best_acceptable[1])
        self.imglog.locations.append(best_acceptable[2])
        if multiple:
            locations = []
            for maximum in feature_maxima:
                locations.append(Location(*maximum[2]))
            self.imglog.log(30, "hybrid")
            return locations
        else:
            log.debug("Best acceptable match with similarity %s at %s",
                      self.imglog.similarities[-1], self.imglog.locations[-1])
            location = Location(*self.imglog.locations[-1])
            self.imglog.log(30, "hybrid")
            return location

    def _hybrid2to1_find(self, needle, haystack):
        """
        Two thirds feature matching and one third template matching.
        Divide the haystack into x,y subregions and perform feature
        matching once for each dx,dy translation of each subregion.

        This method uses advantages of both template and feature
        matching in order to locate the needle.

        Warning: If this search is intensive (you use small frequent
        subregions) please disable or reduce the image logging.

        Note: Currently this method is dangerous due to a possible
        memory leak. Therefore avoid getting closer to a more normal
        template matching or any small size and delta (x,y and dx,dy) that
        will cause too many match attempts.

        Examples:
            1) Normal template matching:

                find_2to1hybrid(n, h, s, n.width, n.height, 1, 1)

            2) Divide the screen into four quadrants and jump with distance
            halves of these quadrants:

                find_2to1hybrid(n, h, s, h.width/2, h.height/2, h.width/4, h.height/4)
        """
        # accumulate one template and multiple feature cases
        ImageLogger.accumulate_logging = True

        x = self.eq.p["find"]["x"].value
        y = self.eq.p["find"]["y"].value
        dx = self.eq.p["find"]["dx"].value
        dy = self.eq.p["find"]["dy"].value
        log.debug("Using 2to1 hybrid matching with x:%s y:%s, dx:%s, dy:%s",
                  x, y, dx, dy)

        ngray = needle.preprocess(gray=True)
        hgray = haystack.preprocess(gray=True)
        hcanvas = haystack.preprocess(gray=False)

        frame_points = []
        frame_points.append((needle.width / 2, needle.height / 2))
        frame_points.extend([(0, 0), (needle.width, 0), (0, needle.height),
                             (needle.width, needle.height)])

        # the translation distance cannot be larger than the haystack
        dx = min(dx, haystack.width)
        dy = min(dy, haystack.height)
        nx = int(math.ceil(float(max(haystack.width - x, 0)) / dx) + 1)
        ny = int(math.ceil(float(max(haystack.height - y, 0)) / dy) + 1)
        log.debug("Dividing haystack into %ix%i pieces", nx, ny)
        result = numpy.zeros((ny, nx))

        locations = {}
        for i in range(nx):
            for j in range(ny):
                left = i * dx
                right = min(haystack.width, i * dx + x)
                up = j * dy
                down = min(haystack.height, j * dy + y)
                log.debug("Region up-down is %s and left-right is %s",
                          (up, down), (left, right))

                haystack_region = hgray[up:down, left:right]
                haystack_region = haystack_region.copy()
                hotmap_region = hcanvas[up:down, left:right]
                hotmap_region = hotmap_region.copy()

                # uncomment this block in order to view the filling of the results
                # (marked with 1.0 when filled) and the different ndarray shapes
                #result[j][i] = 1.0
                log.log(0, "%s", result)
                log.log(0, "shapes: hcanvas %s, hgray %s, ngray %s, res %s\n",
                        hcanvas.shape, hgray.shape, ngray.shape, result.shape)

                res = self._project_features(frame_points, ngray, haystack_region,
                                             self.eq.p["find"]["similarity"].value,
                                             hotmap_region)
                result[j][i] = self.imglog.similarities[-1]

                if res == None:
                    log.debug("No acceptable match in region %s", (i, j))
                    continue
                else:
                    locations[(j, i)] = (left + self.imglog.locations[-1][0],
                                         up + self.imglog.locations[-1][1])
                    self.imglog.locations[-1] = locations[(j, i)]
                    log.debug("Acceptable best match with similarity %s at %s in region %s",
                              self.imglog.similarities[-1], locations[(j, i)], (i, j))

        # release the accumulated logging from subroutines
        ImageLogger.accumulate_logging = False
        self.imglog.log(30, "2to1")
        return result, locations

    def _project_features(self, locations_in_needle, ngray, hgray,
                          similarity, hotmap_canvas=None):
        """
        Wrapper for the internal feature detection, matching and location
        projection used by all public feature matching functions.
        """
        # default logging in case no match is found (further overridden by match stages)
        self.imglog.hotmaps.append(hotmap_canvas)
        self.imglog.locations.append((0, 0))
        self.imglog.similarities.append(0.0)

        log.debug("Performing %s feature matching (no color)",
                  "-".join([self.eq.get_backend("fdetect"),
                            self.eq.get_backend("fextract"),
                            self.eq.get_backend("fmatch")]))
        nkp, ndc, hkp, hdc = self._detect_features(ngray, hgray,
                                                   self.eq.get_backend("fdetect"),
                                                   self.eq.get_backend("fextract"))

        if len(nkp) < 4 or len(hkp) < 4:
            log.debug("No acceptable best match after feature detection: "
                      "only %s needle and %s haystack features detected",
                      len(nkp), len(hkp))
            self.imglog.log(40, "feature")
            return None

        mnkp, mhkp = self._match_features(nkp, ndc, hkp, hdc,
                                          self.eq.get_backend("fmatch"))

        if self.imglog.similarities[-1] < similarity or len(mnkp) < 4:
            log.debug("No acceptable best match after feature matching: "
                      "best match similarity %s is less than required %s",
                      self.imglog.similarities[-1], similarity)
            self.imglog.log(40, "feature")
            return None

        self._project_locations(locations_in_needle, mnkp, mhkp)

        if self.imglog.similarities[-1] < similarity:
            log.debug("No acceptable best match after RANSAC projection: "
                      "best match similarity %s is less than required %s",
                      self.imglog.similarities[-1], similarity)
            self.imglog.log(40, "feature")
            return None
        else:
            log.debug("Best match with similarity %s at %s is acceptable",
                      self.imglog.similarities[-1], self.imglog.locations[-1])
            location = Location(*self.imglog.locations[-1])
            self.imglog.log(30, "feature")
            return location

    def _detect_features(self, ngray, hgray, detect, extract):
        """
        Detect all keypoints and calculate their respective decriptors.
        """
        nkeypoints, hkeypoints = [], []
        nfactor = self.eq.p["fdetect"]["nzoom"].value
        hfactor = self.eq.p["fdetect"]["hzoom"].value

        # zoom in if explicitly set
        if nfactor > 1.0:
            nmat = cv.fromarray(ngray)
            nmat_zoomed = cv.CreateMat(int(nmat.rows * nfactor), int(nmat.cols * nfactor), cv.CV_8UC1)
            log.debug("Zooming x%i needle", nfactor)
            log.log(0, "%s,%s -> %s,%s", nmat.rows, nmat.cols, nmat_zoomed.rows, nmat_zoomed.cols)
            cv.Resize(nmat, nmat_zoomed)
            ngray = numpy.asarray(nmat_zoomed)
        if hfactor > 1.0:
            hmat = cv.fromarray(hgray)
            hmat_zoomed = cv.CreateMat(int(hmat.rows * hfactor), int(hmat.cols * hfactor), cv.CV_8UC1)
            log.debug("Zooming x%i haystack", hfactor)
            log.log(0, "%s,%s -> %s,%s", hmat.rows, hmat.cols, hmat_zoomed.rows, hmat_zoomed.cols)
            cv.Resize(hmat, hmat_zoomed)
            hgray = numpy.asarray(hmat_zoomed)

        if detect == "oldSURF":
            # build the old surf feature detector
            hessian_threshold = self.eq.p["fdetect"]["oldSURFdetect"].value
            detector = cv2.SURF(hessian_threshold)

            (nkeypoints, ndescriptors) = detector.detect(ngray, None, useProvidedKeypoints=False)
            (hkeypoints, hdescriptors) = detector.detect(hgray, None, useProvidedKeypoints=False)

        # include only methods tested for compatibility
        elif (detect in self.eq.algorithms["feature_detectors"]
              and extract in self.eq.algorithms["feature_extractors"]):
            detector = cv2.FeatureDetector_create(detect)
            detector = self.eq.sync_backend_to_params(detector, "fdetect")
            extractor = cv2.DescriptorExtractor_create(extract)
            extractor = self.eq.sync_backend_to_params(extractor, "fextract")

            # keypoints
            nkeypoints = detector.detect(ngray)
            hkeypoints = detector.detect(hgray)

            # feature vectors (descriptors)
            (nkeypoints, ndescriptors) = extractor.compute(ngray, nkeypoints)
            (hkeypoints, hdescriptors) = extractor.compute(hgray, hkeypoints)

        else:
            raise ImageFinderMethodError

        # reduce keypoint coordinates to the original image size
        for nkeypoint in nkeypoints:
            nkeypoint.pt = (int(nkeypoint.pt[0] / nfactor),
                            int(nkeypoint.pt[1] / nfactor))
        for hkeypoint in hkeypoints:
            hkeypoint.pt = (int(hkeypoint.pt[0] / hfactor),
                            int(hkeypoint.pt[1] / hfactor))

        log.debug("Detected %s keypoints in needle and %s in haystack",
                  len(nkeypoints), len(hkeypoints))
        hkp_locations = [hkp.pt for hkp in hkeypoints]
        self.imglog.log_locations(10, hkp_locations, None, 1, 0, 0, 255)

        return (nkeypoints, ndescriptors, hkeypoints, hdescriptors)

    def _match_features(self, nkeypoints, ndescriptors,
                        hkeypoints, hdescriptors, match):
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

                    if smooth_dist1 / smooth_dist2 < self.eq.p["fmatch"]["ratioThreshold"].value:
                        matches2.append(m[0])
                else:
                    matches2.append(m[0])

            log.log(0, "Ratio test result is %i/%i", len(matches2), len(matches))
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

            log.log(0, "Symmetry test result is %i/%i", len(matches2), len(matches))
            return matches2

        # build matchers
        if match in ("in-house-raw", "in-house-region"):
            matcher = InHouseCV()
        # include only methods tested for compatibility
        elif match in self.eq.algorithms["feature_matchers"]:
            # build matcher and match feature vectors
            matcher = cv2.DescriptorMatcher_create(match)
            matcher = self.eq.sync_backend_to_params(matcher, "fmatch")
        else:
            raise ImageFinderMethodError

        # find and filter matches through tests
        if match == "in-house-region":
            matches = matcher.regionMatch(ndescriptors, hdescriptors,
                                          nkeypoints, hkeypoints,
                                          self.eq.p["fmatch"]["refinements"].value,
                                          self.eq.p["fmatch"]["recalc_interval"].value,
                                          self.eq.p["fmatch"]["variants_k"].value,
                                          self.eq.p["fmatch"]["variants_ratio"].value)
        else:
            if self.eq.p["fmatch"]["ratioTest"].value:
                matches = matcher.knnMatch(ndescriptors, hdescriptors, 2)
                matches = ratio_test(matches)
            else:
                matches = matcher.knnMatch(ndescriptors, hdescriptors, 1)
                matches = [m[0] for m in matches]
            if self.eq.p["fmatch"]["symmetryTest"].value:
                if self.eq.p["fmatch"]["ratioTest"].value:
                    hmatches = matcher.knnMatch(hdescriptors, ndescriptors, 2)
                    hmatches = ratio_test(hmatches)
                else:
                    hmatches = matcher.knnMatch(hdescriptors, ndescriptors, 1)
                    hmatches = [hm[0] for hm in hmatches]
                matches = symmetry_test(matches, hmatches)

        # prepare final matches
        match_nkeypoints = []
        match_hkeypoints = []
        matches = sorted(matches, key=lambda x: x.distance)
        for match in matches:
            log.log(0, match.distance)
            match_nkeypoints.append(nkeypoints[match.queryIdx])
            match_hkeypoints.append(hkeypoints[match.trainIdx])

        # these matches are half the way to being good
        mhkp_locations = [mhkp.pt for mhkp in match_hkeypoints]
        self.imglog.log_locations(10, mhkp_locations, None, 2, 0, 255, 255)

        # update the current achieved similarity
        match_similarity = float(len(match_nkeypoints)) / float(len(nkeypoints))
        self.imglog.similarities[-1] = match_similarity
        log.log(0, "%s\\%s -> %f", len(match_nkeypoints),
                len(nkeypoints), match_similarity)

        return (match_nkeypoints, match_hkeypoints)

    def _project_locations(self, locations_in_needle, mnkp, mhkp):
        """
        Calculate the projection of points from the needle in the
        haystack using random sample consensus and the matched
        keypoints between the needle and the haystack.

        Returns a list of (x,y) tuples of the respective locations
        in the haystack.

        Also sets the final similarity and returned location in
        the hotmap.

        Warning: The returned location is always the projected
        point at (0,0) needle coordinates as in template matching,
        i.e. the upper left corner of the image. In case of wild
        transformations of the needle in the haystack this has to
        be reconsidered and the needle center becomes obligatory.

        @param locations_in_needle: (x,y) tuples for each point
        @param mnkp: matched needle keypoints
        @param mhkp: matched haystack keypoints
        """
        # check matches consistency
        assert len(mnkp) == len(mhkp)

        # the match coordinates to be returned
        locations_in_needle.append((0, 0))

        # homography and fundamental matrix as options - homography is considered only
        # for rotation but currently gives better results than the fundamental matrix
        H, mask = cv2.findHomography(numpy.array([kp.pt for kp in mnkp]),
                                     numpy.array([kp.pt for kp in mhkp]), cv2.RANSAC,
                                     self.eq.p["find"]["ransacReprojThreshold"].value)
        # H, mask = cv2.findFundamentalMat(numpy.array([kp.pt for kp in mnkp]),
        #                                 numpy.array([kp.pt for kp in mhkp]),
        #                                 method = cv2.RANSAC, param1 = 10.0,
        #                                 param2 = 0.9)

        # measure total used features for the projected focus point
        true_matches = []
        for kp in mhkp:
            # true matches are also inliers for the homography
            if mask[mhkp.index(kp)][0] == 1:
                true_matches.append(kp)
        tmhkp_locations = [tmhkp.pt for tmhkp in true_matches]
        self.imglog.log_locations(20, tmhkp_locations, None, 3, 0, 255, 0)

        # calculate and project all point coordinates in the needle
        projected = []
        for location in locations_in_needle:
            (ox, oy) = (location[0], location[1])
            orig_center_wrapped = numpy.array([[[ox, oy]]], dtype=numpy.float32)
            log.log(0, "%s %s", orig_center_wrapped.shape, H.shape)
            match_center_wrapped = cv2.perspectiveTransform(orig_center_wrapped, H)
            (mx, my) = (match_center_wrapped[0][0][0], match_center_wrapped[0][0][1])
            projected.append((int(mx), int(my)))

        ransac_similarity = float(len(true_matches)) / float(len(mnkp))
        # override the match similarity with a more precise one
        self.imglog.similarities[-1] = ransac_similarity
        log.log(0, "%s\\%s -> %f", len(true_matches), len(mnkp), ransac_similarity)
        self.imglog.locations[-1] = locations_in_needle.pop()

        return projected

    def _match_template(self, needle, haystack, nocolor, match):
        """
        Match a color or grayscale needle image using the OpenCV
        template matching methods.
        """
        # Sanity check: Needle size must be smaller than haystack
        if haystack.width < needle.width or haystack.height < needle.height:
            log.warning("The size of the searched image (%sx%s) is smaller than its region (%sx%s)",
                        needle.width, needle.height, haystack.width, haystack.height)
            return None

        methods = {"sqdiff": cv2.TM_SQDIFF, "sqdiff_normed": cv2.TM_SQDIFF_NORMED,
                   "ccorr": cv2.TM_CCORR, "ccorr_normed": cv2.TM_CCORR_NORMED,
                   "ccoeff": cv2.TM_CCOEFF, "ccoeff_normed": cv2.TM_CCOEFF_NORMED}
        if match not in methods.keys():
            raise ImageFinderMethodError

        if nocolor:
            gray_needle = needle.preprocess(gray=True)
            gray_haystack = haystack.preprocess(gray=True)
            match = cv2.matchTemplate(gray_haystack, gray_needle, methods[match])
        else:
            opencv_needle = needle.preprocess(gray=False)
            opencv_haystack = haystack.preprocess(gray=False)
            match = cv2.matchTemplate(opencv_haystack, opencv_needle, methods[match])

        return match


class InHouseCV(ImageFinder):

    """
    ImageFinder backend with in-house CV algorithms.
    """

    def __init__(self):
        """Initiate thee CV backend attributes."""
        self.detector = cv2.FeatureDetector_create("ORB")
        self.extractor = cv2.DescriptorExtractor_create("ORB")

    def detect_features(self, needle, haystack):
        """
        In-house feature detect algorithm - currently not fully implemented!

        The current MSER might not be used in the actual implementation.
        """
        opencv_haystack = haystack.preprocess()
        opencv_needle = needle.preprocess()
        hgray = haystack.preprocess(gray=True)
        ngray = needle.preprocess(gray=True)

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

    def regionMatch(self, desc1, desc2, kp1, kp2,
                    refinements=50, recalc_interval=10,
                    variants_k=100, variants_ratio=0.33):
        """
        Use location information to better decide on matched features.

        The knn distance is now only a heuristic for the search of best
        matched set as is information on relative location with regard
        to the other matches.

        @param refinements: number of points to relocate
        @param recalc_interval: recalculation on a number of refinements
        @param variants_k: kNN parameter for to limit the alternative variants
            of a badly positioned feature
        @param variants_ratio: internal ratio test for knnMatch autostop (see below)

        TODO: handle a subset of matches (ignoring some matches if not all features are detected)
        TODO: disable kernel mapping (multiple needle feature mapped to a single haystack feature)
        """
        def ncoord(match):
            return kp1[match.queryIdx].pt

        def hcoord(match):
            return kp2[match.trainIdx].pt

        def rcoord(origin, target):
            # True is right/up or coinciding, False is left/down
            coord = [0, 0]
            if target[0] < origin[0]:
                coord[0] = -1
            elif target[0] > origin[0]:
                coord[0] = 1
            if target[1] < origin[1]:
                coord[1] = -1
            elif target[1] > origin[1]:
                coord[1] = 1
            log.log(0, "%s:%s=%s", origin, target, coord)
            return coord

        def compare_pos(match1, match2):
            hc = rcoord(hcoord(match1), hcoord(match2))
            nc = rcoord(ncoord(match1), ncoord(match2))

            valid_positioning = True
            if hc[0] != nc[0] and hc[0] != 0 and nc[0] != 0:
                valid_positioning = False
            if hc[1] != nc[1] and hc[1] != 0 and nc[1] != 0:
                valid_positioning = False

            log.log(0, "p1:p2 = %s in haystack and %s in needle", hc, nc)
            log.log(0, "is their relative positioning valid? %s", valid_positioning)

            return valid_positioning

        def match_cost(matches, new_match):
            if len(matches) == 0:
                return 0.0

            nominator = sum(float(not compare_pos(match, new_match)) for match in matches)
            denominator = float(len(matches))
            ratio = nominator / denominator
            log.log(0, "model <-> match = %i disagreeing / %i total matches",
                    nominator, denominator)

            # avoid 0 mapping, i.e. giving 0 positional
            # conflict to 0 distance matches or 0 distance
            # to matches with 0 positional conflict
            if ratio == 0.0 and new_match.distance != 0.0:
                ratio = 0.001
            elif new_match.distance == 0.0 and ratio != 0.0:
                new_match.distance = 0.001

            cost = ratio * new_match.distance
            log.log(0, "would be + %f cost", cost)
            log.log(0, "match reduction: %s",
                    cost / max(sum(m.distance for m in matches), 1))

            return cost

        results = self.knnMatch(desc1, desc2, variants_k,
                                1, variants_ratio)
        matches = [variants[0] for variants in results]
        ratings = [None for _ in matches]
        log.log(0, "%i matches in needle to start with", len(matches))

        # minimum one refinement is needed
        refinements = max(1, refinements)
        for i in range(refinements):

            # recalculate all ratings on some interval to save performance
            if i % recalc_interval == 0:
                for j in range(len(matches)):
                    # ratings forced to 0.0 cannot be improved
                    # because there are not better variants to use
                    if ratings[j] != 0.0:
                        ratings[j] = match_cost(matches, matches[j])
                quality = sum(ratings)
                log.debug("Recalculated quality: %s", quality)

                # nothing to improve if quality is perfect
                if quality == 0.0:
                    break

            outlier_index = ratings.index(max(ratings))
            outlier = matches[outlier_index]
            variants = results[outlier_index]
            log.log(0, "outlier m%i with rating %i", outlier_index, max(ratings))
            log.log(0, "%i match variants for needle match %i", len(variants), outlier_index)

            # add the match variant with a minimal cost
            variant_costs = []
            curr_cost_index = variants.index(outlier)
            for j, variant in enumerate(variants):

                # speed up using some heuristics
                if j > 0:
                    # cheap assertion paid for with the speedup
                    assert variants[j].queryIdx == variants[j - 1].queryIdx
                    if variants[j].trainIdx == variants[j - 1].trainIdx:
                        continue
                log.log(0, "variant %i is m%i/%i in n/h", j, variant.queryIdx, variant.trainIdx)
                log.log(0, "variant %i coord in n/h %s/%s", j, ncoord(variant), hcoord(variant))
                log.log(0, "variant distance: %s", variant.distance)

                matches[outlier_index] = variant
                variant_costs.append((j, match_cost(matches, variant)))

            min_cost_index, min_cost = min(variant_costs, key=lambda x: x[1])
            min_cost_variant = variants[min_cost_index]
            # if variant_costs.index(min(variant_costs)) != 0:
            log.log(0, "%s>%s i.e. variant %s", variant_costs, min_cost, min_cost_index)
            matches[outlier_index] = min_cost_variant
            ratings[outlier_index] = min_cost

            # when the best variant is the selected for improvement
            if min_cost_index == curr_cost_index:
                ratings[outlier_index] = 0.0

            # 0.0 is best quality
            log.debug("Overall quality: %s", sum(ratings))
            log.debug("Reduction: %s", sum(ratings) / max(sum(m.distance for m in matches), 1))

        return matches

    def knnMatch(self, desc1, desc2, k=1, desc4kp=1, autostop=0.0):
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
            desc1 = numpy.array(desc1, dtype=numpy.float32).reshape((-1, desc4kp))
            desc2 = numpy.array(desc2, dtype=numpy.float32).reshape((-1, desc4kp))
            log.log(0, "%s %s", desc1.shape, desc2.shape)
        else:
            desc1 = numpy.array(desc1, dtype=numpy.float32)
            desc2 = numpy.array(desc2, dtype=numpy.float32)
        desc_size = desc2.shape[1]

        # kNN training - learn mapping from rows2 to kp2 index
        samples = desc2
        responses = numpy.arange(int(len(desc2) / desc4kp), dtype=numpy.float32)
        log.log(0, "%s %s", len(samples), len(responses))
        knn = cv2.KNearest()
        knn.train(samples, responses, maxK=k)

        matches = []
        # retrieve index and value through enumeration
        for i, descriptor in enumerate(desc1):
            descriptor = numpy.array(descriptor, dtype=numpy.float32).reshape((1, desc_size))
            log.log(0, "%s %s %s", i, descriptor.shape, samples[0].shape)
            kmatches = []
            ratio = 1.0

            for ki in range(k):
                _, res, _, dists = knn.find_nearest(descriptor, ki + 1)
                log.log(0, "%s %s %s", ki, res, dists)
                if len(dists[0]) > 1 and autostop > 0.0:

                    # TODO: perhaps ratio from first to last ki?
                    # smooth to make 0/0 case also defined as 1.0
                    dist1 = dists[0][-2] + 0.0000001
                    dist2 = dists[0][-1] + 0.0000001
                    ratio = dist1 / dist2
                    log.log(0, "%s %s", ratio, autostop)
                    if ratio < autostop:
                        break

                kmatches.append(cv2.DMatch(i, int(res[0][0]), dists[0][-1]))

            matches.append(tuple(kmatches))
        return matches
