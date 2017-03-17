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
import os
import re
try:
    import configparser as config
except ImportError:
    import ConfigParser as config

from settings import GlobalSettings, LocalSettings
from location import Location
from imagelogger import ImageLogger
from errors import *

import logging
log = logging.getLogger('guibender.imagefinder')


class CVParameter(object):
    """A class for a single parameter used for CV backend configuration."""

    def __init__(self, value,
                 min_val=None, max_val=None,
                 delta=1.0, tolerance=0.1,
                 fixed=True):
        """
        Build a computer vision parameter.

        :param value: value of the parameter
        :type value: bool or int or float or None
        :param min_val: lower boundary for the parameter range
        :type min_val: int or float or None
        :param max_val: upper boundary for the parameter range
        :type max_val: int or float or None
        :param float delta: delta for the calibration
                            (no calibration if `delta` < `tolerance`)
        :param float tolerance: tolerance of calibration
        :param bool fixed: whether the parameter is prevented from calibration
        """
        self.value = value
        self.delta = delta
        self.tolerance = tolerance

        # force specific tolerance and delta for bool and
        # int parameters
        if type(value) == bool:
            self.delta = 0.0
            self.tolerance = 1.0
        elif type(value) == int:
            self.delta = 1
            self.tolerance = 0.9

        if min_val != None:
            assert value >= min_val
        if max_val != None:
            assert value <= max_val
        self.range = (min_val, max_val)

        self.fixed = fixed

    def __repr__(self):
        """
        Provide a representation of the parameter for storing and reporting.

        :returns: special syntax representation of the parameter
        :rtype: str
        """
        return ("<value='%s' min='%s' max='%s' delta='%s' tolerance='%s' fixed='%s'>"
                % (self.value, self.range[0], self.range[1], self.delta, self.tolerance, self.fixed))

    @staticmethod
    def from_string(raw):
        """
        Parse a CV parameter from string.

        :param str raw: string representation for the parameter
        :returns: parameter parsed from the representation
        :rtype: :py:class:`CVParameter`
        :raises: :py:class:`ValueError` if unsupported type is encountered
        """
        args = []
        string_args = re.match(r"<value='(.+)' min='([\d.None]+)' max='([\d.None]+)'"
                               r" delta='([\d.]+)' tolerance='([\d.]+)' fixed='(\w+)'>",
                               raw).group(1, 2, 3, 4, 5, 6)
        for arg in string_args:
            if arg == "None":
                arg = None
            elif arg == "True":
                arg = True
            elif arg == "False":
                arg = False
            elif re.match(r"\d+$", arg):
                arg = int(arg)
            elif re.match(r"[\d.]+", arg):
                arg = float(arg)
            else:
                arg = str(arg)

            log.log(0, "%s %s", arg, type(arg))
            args.append(arg)

        log.log(0, "%s", args)
        return CVParameter(*args)


class ImageFinder(LocalSettings):
    """
    Base for all image matching functionality and backends.

    It has implementations with both template matching and feature matching
    algorithms through AutoPy or through the OpenCV library as well as a
    hybrid approach. The image finding methods include finding one or all
    matches above the similarity defined in the configuration of each backend.

    External (image finder) parameters are:
        * detect filter - works for certain detectors and
            determines how many initial features are
            detected in an image (e.g. hessian threshold for
            SURF detector)
        * match filter - determines what part of all matches
            returned by feature matcher remain good matches
        * project filter - determines what part of the good
            matches are considered inliers
        * ratio test - boolean for whether to perform a ratio test
        * symmetry test - boolean for whether to perform a symmetry test

    There are many parameters that could contribute for a good match. They can
    all be manually adjusted or automatically calibrated.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build an image finder and its CV backend settings."""
        super(ImageFinder, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["find"] = "find_methods"
        self.algorithms["find_methods"] = ("autopy", "contour", "template", "feature", "cascade", "hybrid")

        # other attributes
        self.imglog = ImageLogger()
        self.imglog.log = self.log

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="find", reset=False):
        if category != "find":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(ImageFinder, self).configure_backend(backend="cv", reset=True)
        if backend is None:
            backend = GlobalSettings.find_image_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(0, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend
        self.params[category]["similarity"] = CVParameter(0.8, 0.0, 1.0, 0.1, 0.1)
        log.log(0, "%s %s\n", category, self.params[category])

    def configure_backend(self, backend=None, category="find", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="find", reset=False):
        if category != "find":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(ImageFinder, self).synchronize_backend("cv", reset=True)
        # no backend object to sync to
        if backend is None:
            backend = GlobalSettings.find_image_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

    def synchronize_backend(self, backend=None, category="find", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def from_match_file(self, filename_without_extention):
        """
        Read the configuration from a .match file with the given filename.

        :param str filename_without_extention: match filename for the configuration
        :raises: :py:class:`IOError` if the respective match file couldn't be read

        The influence of the read configuration is that of an overwrite, i.e.
        all parameters will be generated (if not already present) and then the
        ones read from the configuration file will be overwritten.
        """
        if len(self.params.keys()) == 0:
            self.configure()

        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        success = parser.read("%s.match" % filename_without_extention)
        # if no file is found throw an exception
        if len(success) == 0:
            raise IOError

        for category in self.params.keys():
            if parser.has_section(category):
                section_backend = parser.get(category, 'backend')
                if section_backend != self.params[category]["backend"]:
                    self.configure_backend(backend=section_backend, category=category, reset=False)
                for option in parser.options(category):
                    if option == "backend":
                        continue
                    param_string = parser.get(category, option)
                    if isinstance(self.params[category][option], CVParameter):
                        param = CVParameter.from_string(param_string)
                        log.log(0, "%s %s", param_string, param)
                    else:
                        param = param_string
                    self.params[category][option] = param

    def to_match_file(self, filename_without_extention):
        """
        Write the configuration in a .match file with the given filename.

        :param str filename_without_extention: match filename for the configuration
        """
        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        sections = self.params.keys()
        for section in sections:
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, 'backend', self.params[section]["backend"])
            for option in self.params[section]:
                log.log(0, "%s %s", section, option)
                parser.set(section, option, self.params[section][option])

        with open("%s.match" % filename_without_extention, 'w') as configfile:
            configfile.write("# IMAGE MATCH DATA\n")
            parser.write(configfile)

    def can_calibrate(self, category, mark):
        """
        Fix the parameters for a given category backend algorithm,
        i.e. disallow the calibrator to change them.

        :param bool mark: whether to mark for calibration
        :param str category: backend category whose parameters are marked
        :raises: :py:class:`UnsupportedBackendError` if `category` is not among the
                 supported backend categories
        """
        if category not in self.categories.keys():
            raise UnsupportedBackendError("Category '%s' not among the "
                                          "supported %s" % (category, self.categories.keys()))

        for param in self.params[category].values():
            if not isinstance(param, CVParameter):
                continue
            # BUG: force fix parameters that have internal bugs
            if category == "fextract" and param == "bytes":
                param.fixed = True
            else:
                param.fixed = not mark

    def find(self, needle, haystack, multiple=False):
        """
        Find all needle images in a haystack image.

        :param needle: image, text, or pattern to look for
        :type needle: :py:class:`image.Target`
        :param haystack: image to look in
        :type haystack: :py:class:`image.Image`
        :param bool multiple: whether to find all matches
        :returns: all found matches (one in most use cases)
        :rtype: [:py:class:`location.Location`]
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Abstract method call - call implementation of this class")

    def log(self, lvl):
        """
        Log images with an arbitrary logging level.

        :param int lvl: logging level for the message
        """
        # below selected logging level
        if lvl < self.imglog.logging_level:
            return
        # logging is being collected for a specific logtype
        elif ImageLogger.accumulate_logging:
            return
        # no hotmaps to log
        elif len(self.imglog.hotmaps) == 0:
            raise MissingHotmapError("No matching was performed in order to be image logged")

        similarity = self.imglog.similarities[-1] if len(self.imglog.similarities) > 0 else 0.0
        name = "imglog%s-3hotmap-%s.png" % (self.imglog.printable_step, similarity)
        self.imglog.dump_hotmap(name, self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class AutoPyMatcher(ImageFinder):
    """Simple matching backend provided by AutoPy."""

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using AutoPy."""
        super(AutoPyMatcher, self).__init__(configure=False, synchronize=False)

        # other attributes
        self._bitmapcache = {}

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="autopy", reset=False):
        if category != "autopy":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(AutoPyMatcher, self).configure_backend(backend="autopy", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(self, backend=None, category="autopy", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        :raises: :py:class:`NotImplementedError` if expecting multiple matches

        See base method for details.

        .. warning:: AutoPy has a bug when finding multiple matches
                     so this is currently not supported.
        """
        if multiple:
            raise NotImplementedError("The backend algorithm AutoPy does not support "
                                      "multiple matches on screen")

        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()
        # prepare a canvas solely for image logging
        self.imglog.hotmaps.append(haystack.pil_image.copy())

        # class-specific dependencies
        from autopy import bitmap
        from tempfile import NamedTemporaryFile

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

        autopy_tolerance = 1.0 - self.params["find"]["similarity"].value
        log.debug("Performing autopy template matching with tolerance %s (color)",
                  autopy_tolerance)

        # TODO: since only the coordinates are available and fuzzy areas of
        # matches are returned we need to ask autopy team for returning
        # the matching rates as well
        coord = autopy_screenshot.find_bitmap(autopy_needle, autopy_tolerance)
        log.debug("Best acceptable match starting at %s", coord)

        if coord is not None:
            self.imglog.locations.append(coord)
            self.imglog.similarities.append(1.0 - autopy_tolerance)
            matches = [Location(coord[0], coord[1])]
            from PIL import ImageDraw
            draw = ImageDraw.Draw(self.imglog.hotmaps[-1])
            draw.rectangle((coord[0], coord[1], coord[0]+needle.width, coord[1]+needle.height),
                           outline=(0,0,255))
            del draw
        else:
            matches = []
        self.imglog.log(30)
        return matches


class ContourMatcher(ImageFinder):
    """
    Contour matching backend provided by OpenCV.

    Essentially, we will find all countours in a binary image,
    preprocessed with Gaussian blur and adaptive threshold and return
    the ones with area (size) similar to the searched image.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's contour matching."""
        super(ContourMatcher, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["contour"] = "contour_extractors"
        self.categories["threshold"] = "threshold_filters"
        self.algorithms["contour_extractors"] = ("mixed",)
        self.algorithms["threshold_filters"] = ("normal", "adaptive", "canny")

        # additional preparation (no synchronization available)
        if configure:
            self.__configure(reset=True)

    def __configure_backend(self, backend=None, category="contour", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if category not in ["contour", "threshold"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(ContourMatcher, self).configure_backend("contour", reset=True)
        if category == "contour" and backend is None:
            backend = "mixed"
        elif category == "threshold" and backend is None:
            backend = "adaptive"
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(0, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend

        if category == "contour":
            # 1 RETR_EXTERNAL, 2 RETR_LIST, 3 RETR_CCOMP, 4 RETR_TREE
            self.params[category]["retrievalMode"] = CVParameter(2, 1, 4)
            # 1 CHAIN_APPROX_NONE, 2 CHAIN_APPROX_SIMPLE, 3 CHAIN_APPROX_TC89_L1, 4 CHAIN_APPROX_TC89_KCOS
            self.params[category]["approxMethod"] = CVParameter(2, 1, 4)
            self.params[category]["minArea"] = CVParameter(9, 0, None)
            # 1 L1 method, 2 L2 method, 3 L3 method
            self.params[category]["contoursMatch"] = CVParameter(1, 1, 3)
        elif category == "threshold":
            # 1 normal, 2 median, 3 gaussian, 4 none
            self.params[category]["blurType"] = CVParameter(4, 1, 4)
            self.params[category]["blurKernelSize"] = CVParameter(5, 1, None)
            self.params[category]["blurKernelSigma"] = CVParameter(0, 0, None)
            if backend == "normal":
                self.params[category]["thresholdValue"] = CVParameter(122, 0, 255)
                self.params[category]["thresholdMax"] = CVParameter(255, 0, 255)
                self.params[category]["thresholdType"] = CVParameter(1, 1, 5)
            elif backend == "adaptive":
                self.params[category]["thresholdMax"] = CVParameter(255, 0, 255)
                self.params[category]["adaptiveMethod"] = CVParameter(1, 1, 2)
                self.params[category]["thresholdType"] = CVParameter(1, 1, 2)
                self.params[category]["blockSize"] = CVParameter(11, 1, None)
                self.params[category]["constant"] = CVParameter(2, 1, None)
            elif backend == "canny":
                self.params[category]["threshold1"] = CVParameter(100.0, 0.0, None)
                self.params[category]["threshold2"] = CVParameter(1000.0, 0.0, None)

    def configure_backend(self, backend=None, category="contour", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __configure(self, threshold_filter=None, reset=True):
        self.__configure_backend(category="contour", reset=reset)
        self.__configure_backend(threshold_filter, "threshold")

    def configure(self, threshold_filter=None, reset=True):
        """
        Custom implementation of the base method.

        :param threshold_filter: name of a preselected backend
        :type threshold_filter: str or None
        """
        self.__configure(threshold_filter, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        See base method for details.

        First extract all contours from a binary (boolean, threshold) version of
        the needle and haystack and then match the needle contours with one or
        more sets of contours in the haystack image. The number of needle matches
        depends on the set similarity and can be improved by requiring minimal
        area for the contours to be considered.
        """
        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        # class-specific dependencies
        import cv2
        import numpy

        orig_needle = numpy.array(needle.pil_image)
        thresh_needle = self._binarize_image(orig_needle, log=False)
        countours_needle = thresh_needle.copy()
        needle_contours = self._extract_contours(countours_needle, log=False)

        orig_haystack = numpy.array(haystack.pil_image)
        thresh_haystack = self._binarize_image(orig_haystack, log=True)
        countours_haystack = thresh_haystack.copy()
        haystack_contours = self._extract_contours(countours_haystack, log=True)

        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))

        distances = numpy.ones((len(haystack_contours), len(needle_contours)))
        for i, hcontour in enumerate(haystack_contours):
            if cv2.contourArea(hcontour) < self.params["contour"]["minArea"].value:
                continue
            for j, ncontour in enumerate(needle_contours):
                if cv2.contourArea(ncontour) < self.params["contour"]["minArea"].value:
                    continue
                distances[i,j] = cv2.matchShapes(hcontour, ncontour, self.params["contour"]["contoursMatch"].value, 0)
                assert distances[i,j] >= 0.0

        locations = []
        nx, ny, nw, nh = cv2.boundingRect(numpy.concatenate(needle_contours, axis=0))
        while True:
            matching_haystack_contours = []
            matching_haystack_distances = numpy.zeros(len(needle_contours))
            for j in range(len(needle_contours)):
                matching_haystack_distances[j] = numpy.min(distances[:,j])
                index = numpy.where(distances[:,j] == matching_haystack_distances[j])
                # we don't allow collapsing into the same needle contour, i.e.
                # the map from the needle to the haystack contours is injective
                # -> so here we cross the entire row rather than one value in it
                distances[index[0][0],:] = numpy.max(distances[:,j])
                matching_haystack_contours.append(haystack_contours[index[0][0]])
            average_distance = numpy.average(matching_haystack_distances)
            required_distance = 1.0 - self.params["find"]["similarity"].value
            logging.debug("Average distance to next needle shape is %s of max allowed %s",
                          average_distance, required_distance)
            if average_distance > required_distance:
                break
            else:
                shape = numpy.concatenate(matching_haystack_contours, axis=0)
                x, y, w, h = cv2.boundingRect(shape)
                # calculate needle upleft and downright points to return its (0,0) location
                needle_upleft = (max(int((x-nx)*float(w)/nw), 0), max(int((y-ny)*float(h)/nh), 0))
                needle_downright = (min(int(needle_upleft[0]+needle.width*float(w)/nw), haystack.width),
                                    min(int(needle_upleft[1]+needle.height*float(h)/nh), haystack.height))
                cv2.rectangle(self.imglog.hotmaps[-1], needle_upleft, needle_downright, (0,0,0), 2)
                cv2.rectangle(self.imglog.hotmaps[-1], needle_upleft, needle_downright, (255,255,255), 1)
                # NOTE: to extract the region of interest just do:
                # roi = thresh_haystack[y:y+h,x:x+w]
                self.imglog.similarities.append(1.0 - average_distance)
                self.imglog.locations.append(needle_upleft)
                locations.append(Location(*needle_upleft))

        self.imglog.log(30)
        return locations

    def _binarize_image(self, image, log=False):
        import cv2
        # blur first in order to avoid unwonted edges caused from noise
        blurSize = self.params["threshold"]["blurKernelSize"].value
        blurDeviation = self.params["threshold"]["blurKernelSigma"].value
        gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        if self.params["threshold"]["blurType"].value == 1:
            blur_image = cv2.blur(gray_image, (blurSize,blurSize))
        elif self.params["threshold"]["blurType"].value == 2:
            blur_image = cv2.medianBlur(gray_image, (blurSize,blurSize))
        elif self.params["threshold"]["blurType"].value == 3:
            blur_image = cv2.GaussianBlur(gray_image, (blurSize,blurSize), blurDeviation)
        elif self.params["threshold"]["blurType"].value == 4:
            blur_image = gray_image

        # second stage: thresholding
        if self.params["threshold"]["backend"] == "normal":
            _, thresh_image = cv2.threshold(blur_image,
                                             self.params["threshold"]["thresholdValue"].value,
                                             self.params["threshold"]["thresholdMax"].value,
                                             self.params["threshold"]["thresholdType"].value)
        elif self.params["threshold"]["backend"] == "adaptive":
            thresh_image = cv2.adaptiveThreshold(blur_image,
                                                  self.params["threshold"]["thresholdMax"].value,
                                                  self.params["threshold"]["adaptiveMethod"].value,
                                                  self.params["threshold"]["thresholdType"].value,
                                                  self.params["threshold"]["blockSize"].value,
                                                  self.params["threshold"]["constant"].value)
        elif self.params["threshold"]["backend"] == "canny":
            thresh_image = cv2.Canny(blur_image,
                                      self.params["threshold"]["threshold1"].value,
                                      self.params["threshold"]["threshold2"].value)

        if log:
            self.imglog.hotmaps.append(thresh_image)
        return thresh_image

    def _extract_contours(self, countours_image, log=False):
        import cv2
        _, contours, hierarchy = cv2.findContours(countours_image,
                                                  self.params["contour"]["retrievalMode"].value,
                                                  self.params["contour"]["approxMethod"].value)
        image_contours = [cv2.approxPolyDP(cnt, 3, True) for cnt in contours]
        if log:
            cv2.drawContours(countours_image, image_contours, -1, (255,255,255))
            self.imglog.hotmaps.append(countours_image)
        return image_contours

    def log(self, lvl):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        # below selected logging level
        if lvl < self.imglog.logging_level:
            return
        # logging is being collected for a specific logtype
        elif ImageLogger.accumulate_logging:
            return
        # no hotmaps to log
        elif len(self.imglog.hotmaps) == 0:
            raise MissingHotmapError("No matching was performed in order to be image logged")

        self.imglog.dump_hotmap("imglog%s-3hotmap-threshold.png" % self.imglog.printable_step,
                                self.imglog.hotmaps[0])
        self.imglog.dump_hotmap("imglog%s-3hotmap-contours.png" % self.imglog.printable_step,
                                self.imglog.hotmaps[1])

        similarity = self.imglog.similarities[-1] if len(self.imglog.similarities) > 0 else 0.0
        self.imglog.dump_hotmap("imglog%s-3hotmap-%s.png" % (self.imglog.printable_step, similarity),
                                self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class TemplateMatcher(ImageFinder):
    """Template matching backend provided by OpenCV."""

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's template matching."""
        super(TemplateMatcher, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["template"] = "template_matchers"
        self.algorithms["template_matchers"] = ("sqdiff", "ccorr", "ccoeff","sqdiff_normed",
                                                 "ccorr_normed", "ccoeff_normed")

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="template", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if category != "template":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(TemplateMatcher, self).configure_backend("template", reset=True)
        if backend is None:
            backend = GlobalSettings.template_match_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(0, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend
        self.params[category]["nocolor"] = CVParameter(False)
        log.log(0, "%s %s\n", category, self.params[category])

    def configure_backend(self, backend=None, category="template", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        :raises: :py:class:`UnsupportedBackendError` if the choice of template
                 matches is not among the supported ones

        See base method for details.
        """
        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        if self.params["template"]["backend"] not in self.algorithms["template_matchers"]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (self.params["template"]["backend"],
                                                  self.algorithms["template_matchers"]))
        match_template = self.params["template"]["backend"]
        no_color = self.params["template"]["nocolor"].value
        log.debug("Performing opencv-%s multiple template matching %s color",
                  match_template, "without" if no_color else "with")
        result = self._match_template(needle, haystack, no_color, match_template)
        if result is None:
            log.warning("OpenCV's template matching returned no result")
            return []
        # switch max and min for sqdiff and sqdiff_normed (to always look for max)
        if self.params["template"]["backend"] in ("sqdiff", "sqdiff_normed"):
            result = 1.0 - result

        import cv2
        import numpy
        universal_hotmap = result * 255.0
        final_hotmap = numpy.array(self.imglog.haystack.pil_image)
        if self.params["template"]["nocolor"].value:
            final_hotmap = cv2.cvtColor(final_hotmap, cv2.COLOR_RGB2GRAY)

        # extract maxima once for each needle size region
        similarity = self.params["find"]["similarity"].value
        maxima = []
        while True:

            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
            # BUG: Due to an OpenCV bug sqdiff_normed might return a similarity > 1.0
            # although it must be normalized (i.e. between 0 and 1) so patch this and
            # other possible similar bugs
            maxVal = min(max(maxVal, 0.0), 1.0)
            log.debug('Best match with value %s (similarity %s) and location (x,y) %s',
                      str(maxVal), similarity, str(maxLoc))

            if maxVal < similarity:
                if len(maxima) == 0:
                    self.imglog.similarities.append(maxVal)
                    self.imglog.locations.append(maxLoc)
                    current_hotmap = numpy.copy(universal_hotmap)
                    cv2.circle(current_hotmap, (maxLoc[0],maxLoc[1]), int(30*maxVal), (255,255,255))
                    self.imglog.hotmaps.append(current_hotmap)
                    self.imglog.hotmaps.append(final_hotmap)

                log.debug("Best match is not acceptable")
                break
            else:
                self.imglog.similarities.append(maxVal)
                self.imglog.locations.append(maxLoc)
                current_hotmap = numpy.copy(universal_hotmap)
                cv2.circle(current_hotmap, (maxLoc[0],maxLoc[1]), int(30*maxVal), (255,255,255))
                x, y = maxLoc
                cv2.rectangle(final_hotmap, (x, y), (x+needle.width, y+needle.height), (0,0,0), 2)
                cv2.rectangle(final_hotmap, (x, y), (x+needle.width, y+needle.height), (255,255,255), 1)
                self.imglog.hotmaps.append(current_hotmap)
                log.debug("Best match is acceptable")
                maxima.append(Location(maxLoc[0], maxLoc[1]))
                if similarity == 0.0:
                    # return just one match if no similarity requirement
                    break

            res_w = haystack.width - needle.width + 1
            res_h = haystack.height - needle.height + 1
            match_x0 = max(maxLoc[0] - int(0.5 * needle.width), 0)
            match_x1 = min(maxLoc[0] + int(0.5 * needle.width), res_w)
            match_y0 = max(maxLoc[1] - int(0.5 * needle.height), 0)
            match_y1 = min(maxLoc[1] + int(0.5 * needle.height), res_h)

            # log this only if performing deep internal debugging
            log.log(0, "Wipe image matches in x [%s, %s]/[%s, %s]",
                    match_x0, match_x1, 0, res_w)
            log.log(0, "Wipe image matches in y [%s, %s]/[%s, %s]",
                    match_y0, match_y1, 0, res_h)

            # clean found image to look for next safe distance match
            result[match_y0:match_y1,match_x0:match_x1] = 0.0

            log.log(0, "Total maxima up to the point are %i", len(maxima))
        log.debug("A total of %i matches found", len(maxima))
        self.imglog.hotmaps.append(final_hotmap)
        self.imglog.log(30)

        return maxima

    def _match_template(self, needle, haystack, nocolor, method):
        """
        EXTRA DOCSTRING: Template matching backend - wrapper.

        Match a color or grayscale needle image using the OpenCV
        template matching methods.
        """
        # sanity check: needle size must be smaller than haystack
        if haystack.width < needle.width or haystack.height < needle.height:
            log.warning("The size of the searched image (%sx%s) is smaller than its region (%sx%s)",
                        needle.width, needle.height, haystack.width, haystack.height)
            return None

        import cv2
        import numpy
        methods = {"sqdiff": cv2.TM_SQDIFF, "sqdiff_normed": cv2.TM_SQDIFF_NORMED,
                   "ccorr": cv2.TM_CCORR, "ccorr_normed": cv2.TM_CCORR_NORMED,
                   "ccoeff": cv2.TM_CCOEFF, "ccoeff_normed": cv2.TM_CCOEFF_NORMED}
        if method not in methods.keys():
            raise UnsupportedBackendError("Supported algorithms are in conflict")

        numpy_needle = numpy.array(needle.pil_image)
        numpy_haystack = numpy.array(haystack.pil_image)
        if nocolor:
            gray_needle = cv2.cvtColor(numpy_needle, cv2.COLOR_RGB2GRAY)
            gray_haystack = cv2.cvtColor(numpy_haystack, cv2.COLOR_RGB2GRAY)
            match = cv2.matchTemplate(gray_haystack, gray_needle, methods[method])
        else:
            match = cv2.matchTemplate(numpy_haystack, numpy_needle, methods[method])

        return match

    def log(self, lvl):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        # below selected logging level
        if lvl < self.imglog.logging_level:
            return
        # logging is being collected for a specific logtype
        elif ImageLogger.accumulate_logging:
            return
        # no hotmaps to log
        elif len(self.imglog.hotmaps) == 0:
            raise MissingHotmapError("No matching was performed in order to be image logged")

        for i in range(len(self.imglog.similarities)):
            name = "imglog%s-3hotmap-template%s-%s.png" % (self.imglog.printable_step,
                                                           i + 1, self.imglog.similarities[i])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[i])

        name = "imglog%s-3hotmap-template.png" % self.imglog.printable_step
        self.imglog.dump_hotmap(name, self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class FeatureMatcher(ImageFinder):
    """
    Feature matching backend provided by OpenCV.

    .. note:: SURF and SIFT are proprietary algorithms and are not available
        by default in newer OpenCV versions (>3.0).
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's feature matching."""
        super(FeatureMatcher, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["feature"] = "feature_projectors"
        self.categories["fdetect"] = "feature_detectors"
        self.categories["fextract"] = "feature_extractors"
        self.categories["fmatch"] = "feature_matchers"
        self.algorithms["feature_projectors"] = ("mixed",)
        self.algorithms["feature_matchers"] = ("BruteForce", "BruteForce-L1", "BruteForce-Hamming",
                                               "BruteForce-Hamming(2)")
        self.algorithms["feature_detectors"] = ("ORB", "BRISK", "KAZE", "AKAZE", "MSER",
                                                  "AgastFeatureDetector", "FastFeatureDetector", "GFTTDetector",
                                                 "SimpleBlobDetector", "oldSURF")
        # TODO: we could also support "StereoSGBM" but it needs initialization arguments
        self.algorithms["feature_extractors"] = ("ORB", "BRISK", "KAZE", "AKAZE")

        # other attributes
        self._detector = None
        self._extractor = None
        self._matcher = None

        # additional preparation
        if configure:
            self.__configure(reset=True)
        if synchronize:
            self.__synchronize(reset=False)

    def __configure_backend(self, backend=None, category="feature", reset=False):
        if category not in ["feature", "fdetect", "fextract", "fmatch"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(FeatureMatcher, self).configure_backend("feature", reset=True)
        if category == "feature" and backend is None:
            backend = "mixed"
        elif category == "fdetect" and backend is None:
            backend = GlobalSettings.feature_detect_backend
        elif category == "fextract" and backend is None:
            backend = GlobalSettings.feature_extract_backend
        elif category == "fmatch" and backend is None:
            backend = GlobalSettings.feature_match_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(0, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend

        if category == "feature":
            # 0 for homography, 1 for fundamental matrix
            self.params[category]["projectionMethod"] = CVParameter(0, 0, 1, None)
            self.params[category]["ransacReprojThreshold"] = CVParameter(0.0, 0.0, 200.0, 10.0, 1.0)
            self.params[category]["minDetectedFeatures"] = CVParameter(4, 1, None)
            self.params[category]["minMatchedFeatures"] = CVParameter(4, 1, None)
            # 0 for matched/detected ratio, 1 for projected/matched ratio
            self.params[category]["similarityRatio"] = CVParameter(1, 0, 1, None)
        elif category == "fdetect":
            self.params[category]["nzoom"] = CVParameter(1.0, 1.0, 10.0, 1.0, 1.0)
            self.params[category]["hzoom"] = CVParameter(1.0, 1.0, 10.0, 1.0, 1.0)

            if backend == "oldSURF":
                self.params[category]["oldSURFdetect"] = CVParameter(85)
                return
            else:
                import cv2
                feature_detector_create = getattr(cv2, "%s_create" % backend)
                self._detector = backend_obj = feature_detector_create()

        elif category == "fextract":
            import cv2
            descriptor_extractor_create = getattr(cv2, "%s_create" % backend)
            self._extractor = backend_obj = descriptor_extractor_create()

        elif category == "fmatch":
            if backend == "in-house-region":
                self.params[category]["refinements"] = CVParameter(50, 1, None)
                self.params[category]["recalc_interval"] = CVParameter(10, 1, None)
                self.params[category]["variants_k"] = CVParameter(100, 1, None)
                self.params[category]["variants_ratio"] = CVParameter(0.33, 0.0001, 1.0)
                return
            else:
                self.params[category]["ratioThreshold"] = CVParameter(0.65, 0.0, 1.0, 0.1)
                self.params[category]["ratioTest"] = CVParameter(False)
                self.params[category]["symmetryTest"] = CVParameter(False)

                # no other parameters are used for the in-house-raw matching
                if backend == "in-house-raw":
                    return
                else:

                    import cv2
                    # NOTE: descriptor matcher creation is kept the old way while feature
                    # detection and extraction not - example of the untidy maintenance of OpenCV
                    self._matcher = backend_obj = cv2.DescriptorMatcher_create(backend)

                    # BUG: a bug of OpenCV leads to crash if parameters
                    # are extracted from the matcher interface although
                    # the API supports it - skip fmatch for now
                    return

        # examine the interface of the OpenCV backend to add extra parameters
        if category in ["fdetect", "fextract", "fmatch"]:
            log.log(0, "%s %s", backend_obj, dir(backend_obj))
            for attribute in dir(backend_obj):
                if not attribute.startswith("get"):
                    continue
                param = attribute.replace("get", "")
                get_param = getattr(backend_obj, attribute)
                val = get_param()
                if type(val) not in [bool, int, float, type(None)]:
                    continue

                # give more information about some better known parameters
                if category in ("fdetect", "fextract") and param == "firstLevel":
                    self.params[category][param] = CVParameter(val, 0, 100)
                elif category in ("fdetect", "fextract") and param == "nFeatures":
                    self.params[category][param] = CVParameter(val, delta=100)
                elif category in ("fdetect", "fextract") and param == "WTA_K":
                    self.params[category][param] = CVParameter(val, 2, 4)
                elif category in ("fdetect", "fextract") and param == "scaleFactor":
                    self.params[category][param] = CVParameter(val, 1.01, 2.0)
                else:
                    self.params[category][param] = CVParameter(val)
                log.debug("%s=%s", param, val)

        log.log(0, "%s %s\n", category, self.params[category])

    def configure_backend(self, backend=None, category="feature", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __configure(self, feature_detect=None, feature_extract=None,
                    feature_match=None, reset=True):
        self.__configure_backend(category="feature", reset=reset)
        self.__configure_backend(feature_detect, "fdetect")
        self.__configure_backend(feature_extract, "fextract")
        self.__configure_backend(feature_match, "fmatch")

    def configure(self, feature_detect=None, feature_extract=None,
                  feature_match=None, reset=True):
        """
        Custom implementation of the base method.

        :param feature_detect: name of a preselected backend
        :type feature_detect: str or None
        :param feature_extract: name of a preselected backend
        :type feature_extract: str or None
        :param feature_match: name of a preselected backend
        :type feature_match: str or None
        """
        self.__configure(feature_detect, feature_extract, feature_match, reset)

    def __synchronize_backend(self, backend=None, category="feature", reset=False):
        if category not in ["feature", "fdetect", "fextract", "fmatch"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(FeatureMatcher, self).synchronize_backend("feature", reset=True)
        backend_obj = None
        if category == "feature":
            # nothing to sync
            return
        elif category == "fdetect":
            backend_obj = self._detector
        elif category == "fextract":
            backend_obj = self._extractor
        elif category == "fmatch":
            backend_obj = self._matcher
            # BUG: a bug of OpenCV leads to crash if parameters
            # are extracted from the matcher interface although
            # the API supports it - skip fmatch for now
            return
        if backend_obj is None or (backend is not None and backend_obj.__class__.__name__ != backend):
            backend = category if backend is None else backend
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

        if category == "fdetect" and self.params[category]["backend"] == "oldSURF":
            pass
        else:
            for attribute in dir(backend_obj):
                if not attribute.startswith("get"):
                    continue
                param = attribute.replace("get", "")
                if param in self.params[category]:
                    val = self.params[category][param].value
                    set_attribute = attribute.replace("get", "set")
                    # some getters might not have corresponding setters
                    if not hasattr(backend_obj, set_attribute):
                        continue
                    set_param = getattr(backend_obj, set_attribute)
                    set_param(val)
                    log.log(0, "Synced %s to %s", param, val)
                    self.params[category][param].value = val
        if category == "fdetect":
            self._detector = backend_obj
        elif category == "fextract":
            self._extractor = backend_obj
        elif category == "fmatch":
            self._matcher = backend_obj

    def synchronize_backend(self, backend=None, category="feature", reset=False):
        """
        Custom implementation of the base method.

        :param str category: supported category, see `algorithms`

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def __synchronize(self, feature_detect=None, feature_extract=None,
                      feature_match=None, reset=True):
        self.__synchronize_backend(category="feature", reset=reset)
        self.__synchronize_backend(feature_detect, "fdetect")
        self.__synchronize_backend(feature_extract, "fextract")
        self.__synchronize_backend(feature_match, "fmatch")

    def synchronize(self, feature_detect=None, feature_extract=None,
                    feature_match=None, reset=True):
        """
        Custom implementation of the base method.

        :param feature_detect: name of a preselected backend
        :type feature_detect: str or None
        :param feature_extract: name of a preselected backend
        :type feature_extract: str or None
        :param feature_match: name of a preselected backend
        :type feature_match: str or None
        """
        self.__synchronize(feature_detect, feature_extract, feature_match, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        :raises: :py:class:`NotImplementedError` if expecting multiple matches

        See base method for details.

        .. warning:: Finding multiple matches is currently not supported.

        Available methods are: a combination of feature detector,
        extractor, and matcher.
        """
        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        if multiple:
            raise NotImplementedError("The feature matcher backend does not support "
                                      "multiple matches on screen")

        import cv2
        import numpy
        ngray = cv2.cvtColor(numpy.array(needle.pil_image), cv2.COLOR_RGB2GRAY)
        hgray = cv2.cvtColor(numpy.array(haystack.pil_image), cv2.COLOR_RGB2GRAY)
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))

        # project more points for debugging purposes and image logging
        frame_points = []
        frame_points.extend([(0, 0), (needle.width, 0), (0, needle.height),
                             (needle.width, needle.height)])
        frame_points.append((needle.width / 2, needle.height / 2))

        similarity = self.params["find"]["similarity"].value
        coord = self._project_features(frame_points, ngray, hgray, similarity)
        matches = [coord] if coord is not None else []

        return matches

    def _project_features(self, locations_in_needle, ngray, hgray, similarity):
        """
        EXTRA DOCSTRING: Feature matching backend - wrapper.

        Wrapper for the internal feature detection, matching and location
        projection used by all public feature matching functions.
        """
        # default logging in case no match is found (further overridden by match stages)
        self.imglog.locations.append((0, 0))
        self.imglog.similarities.append(0.0)

        log.debug("Performing %s feature matching (no color)",
                  "-".join([self.params["fdetect"]["backend"],
                            self.params["fextract"]["backend"],
                            self.params["fmatch"]["backend"]]))
        nkp, ndc, hkp, hdc = self._detect_features(ngray, hgray,
                                                   self.params["fdetect"]["backend"],
                                                   self.params["fextract"]["backend"])

        min_features = self.params["feature"]["minDetectedFeatures"].value
        if len(nkp) < min_features or len(hkp) < min_features:
            log.debug("No acceptable best match after feature detection: "
                      "only %s\%s needle and %s\%s haystack features detected",
                      len(nkp), min_features, len(hkp), min_features)
            self.imglog.log(40)
            return None

        mnkp, mhkp = self._match_features(nkp, ndc, hkp, hdc,
                                          self.params["fmatch"]["backend"])

        min_features = self.params["feature"]["minMatchedFeatures"].value
        if self.imglog.similarities[-1] < similarity or len(mnkp) < min_features:
            log.debug("No acceptable best match after feature matching:\n"
                      "- matched features %s of %s required\n"
                      "- best match similarity %s of %s required",
                      len(mnkp), min_features,
                      self.imglog.similarities[-1], similarity)
            self.imglog.log(40)
            return None

        locations_in_haystack = self._project_locations(locations_in_needle, mnkp, mhkp)
        if self.imglog.similarities[-1] < similarity:
            log.debug("No acceptable best match after RANSAC projection: "
                      "best match similarity %s is less than required %s",
                      self.imglog.similarities[-1], similarity)
            self.imglog.log(40)
            return None
        else:
            self._log_features(30, self.imglog.locations, self.imglog.hotmaps[-1], 3, 0, 0, 255)
            location = Location(*locations_in_haystack[0])
            self.imglog.log(30)
            return location

    def _detect_features(self, ngray, hgray, detect, extract):
        """
        EXTRA DOCSTRING: Feature matching backend - detection/extraction stage (1).

        Detect all keypoints and calculate their respective decriptors.
        """
        nkeypoints, hkeypoints = [], []
        nfactor = self.params["fdetect"]["nzoom"].value
        hfactor = self.params["fdetect"]["hzoom"].value

        # zoom in if explicitly set
        import cv2
        if nfactor > 1.0:
            log.debug("Zooming x%i needle", nfactor)
            ngray = cv2.resize(ngray, None, fx=nfactor, fy=nfactor)
        if hfactor > 1.0:
            log.debug("Zooming x%i haystack", hfactor)
            hgray = cv2.resize(hgray, None, fx=hfactor, fy=hfactor)

        if detect == "oldSURF":
            # build the old surf feature detector
            hessian_threshold = self.params["fdetect"]["oldSURFdetect"].value
            detector = cv2.SURF(hessian_threshold)

            (nkeypoints, ndescriptors) = detector.detect(ngray, None, useProvidedKeypoints=False)
            (hkeypoints, hdescriptors) = detector.detect(hgray, None, useProvidedKeypoints=False)

        # include only methods tested for compatibility
        elif (detect in self.algorithms["feature_detectors"]
              and extract in self.algorithms["feature_extractors"]):
            self.synchronize_backend(category="fdetect")
            self.synchronize_backend(category="fextract")

            # keypoints
            nkeypoints = self._detector.detect(ngray)
            hkeypoints = self._detector.detect(hgray)

            # feature vectors (descriptors)
            (nkeypoints, ndescriptors) = self._extractor.compute(ngray, nkeypoints)
            (hkeypoints, hdescriptors) = self._extractor.compute(hgray, hkeypoints)

        else:
            raise UnsupportedBackendError("Feature detector %s is not among the supported"
                                          "ones %s" % (detect, self.algorithms[self.categories["fdetect"]]))

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
        self._log_features(10, hkp_locations, self.imglog.hotmaps[-4], 3, 255, 0, 0)

        return (nkeypoints, ndescriptors, hkeypoints, hdescriptors)

    def _match_features(self, nkeypoints, ndescriptors,
                        hkeypoints, hdescriptors, match):
        """
        EXTRA DOCSTRING: Feature matching backend - matching stage (2).

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

                    if smooth_dist1 / smooth_dist2 < self.params["fmatch"]["ratioThreshold"].value:
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
            import cv2
            matches2 = []
            for nm in nmatches:
                for hm in hmatches:

                    if nm.queryIdx == hm.trainIdx and nm.trainIdx == hm.queryIdx:
                        m = cv2.DMatch(nm.queryIdx, nm.trainIdx, nm.distance)
                        matches2.append(m)
                        break

            log.log(0, "Symmetry test result is %i/%i", len(matches2), len(matches))
            return matches2

        # include only methods tested for compatibility
        if match in self.algorithms["feature_matchers"]:
            # build matcher and match feature vectors
            self.synchronize_backend(category="fmatch")
        else:
            raise UnsupportedBackendError("Feature detector %s is not among the supported"
                                          "ones %s" % (match, self.algorithms[self.categories["fmatch"]]))

        # find and filter matches through tests
        if match == "in-house-region":
            matches = self._matcher.regionMatch(ndescriptors, hdescriptors,
                                                nkeypoints, hkeypoints,
                                                self.params["fmatch"]["refinements"].value,
                                                self.params["fmatch"]["recalc_interval"].value,
                                                self.params["fmatch"]["variants_k"].value,
                                                self.params["fmatch"]["variants_ratio"].value)
        else:
            if self.params["fmatch"]["ratioTest"].value:
                matches = self._matcher.knnMatch(ndescriptors, hdescriptors, 2)
                matches = ratio_test(matches)
            else:
                matches = self._matcher.knnMatch(ndescriptors, hdescriptors, 1)
                matches = [m[0] for m in matches]
            if self.params["fmatch"]["symmetryTest"].value:
                if self.params["fmatch"]["ratioTest"].value:
                    hmatches = self._matcher.knnMatch(hdescriptors, ndescriptors, 2)
                    hmatches = ratio_test(hmatches)
                else:
                    hmatches = self._matcher.knnMatch(hdescriptors, ndescriptors, 1)
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
        self._log_features(10, mhkp_locations, self.imglog.hotmaps[-3], 2, 255, 255, 0)

        match_similarity = float(len(match_nkeypoints)) / float(len(nkeypoints))
        # update the current achieved similarity if matching similarity is used:
        # won't be updated anymore if self.params["feature"]["similarityRatio"].value == 0
        self.imglog.similarities[-1] = match_similarity
        log.log(0, "%s\\%s -> %f", len(match_nkeypoints),
                len(nkeypoints), match_similarity)

        return (match_nkeypoints, match_hkeypoints)

    def _project_locations(self, locations_in_needle, mnkp, mhkp):
        """
        EXTRA DOCSTRING: Feature matching backend - projecting stage (3).

        Calculate the projection of points from the needle in the
        haystack using random sample consensus and the matched
        keypoints between the needle and the haystack.

        In particular, take the locations in the need as (x,y) tuples
        for each point, the matched needle keypoints, and the matched
        haystack keypoints and return a list of (x,y) tuples of the
        respective locations in the haystack. Also, set the final
        similarity and returned location in the hotmap.

        .. warning:: The returned location is always the projected
            point at (0,0) needle coordinates as in template matching,
            i.e. the upper left corner of the image. In case of wild
            transformations of the needle in the haystack this has to
            be reconsidered and the needle center becomes obligatory.
        """
        # check matches consistency
        assert len(mnkp) == len(mhkp)

        import cv2
        import numpy
        # homography and fundamental matrix as options - homography is considered only
        # for rotation but currently gives better results than the fundamental matrix
        if self.params["feature"]["projectionMethod"].value == 0:
            H, mask = cv2.findHomography(numpy.array([kp.pt for kp in mnkp]),
                                         numpy.array([kp.pt for kp in mhkp]), cv2.RANSAC,
                                         self.params["feature"]["ransacReprojThreshold"].value)
        elif self.params["feature"]["projectionMethod"].value == 1:
            H, mask = cv2.findFundamentalMat(numpy.array([kp.pt for kp in mnkp]),
                                             numpy.array([kp.pt for kp in mhkp]),
                                             method = cv2.RANSAC, param1 = 10.0,
                                             param2 = 0.9)
        else:
            raise ValueError("Unsupported projection method - use 0 for homography and "
                             "1 for fundamentlal matrix")

        # measure total used features for the projected focus point
        if H is None or mask is None:
            log.log(30, "Homography error occurred during feature matching")
            self.imglog.similarities[-1] = 0.0
            return []
        true_matches = []
        for i, kp in enumerate(mhkp):
            # true matches are also inliers for the homography
            if mask[i][0] == 1:
                true_matches.append(kp)
        tmhkp_locations = [tmhkp.pt for tmhkp in true_matches]
        self._log_features(20, tmhkp_locations, self.imglog.hotmaps[-2], 1, 0, 255, 0)

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
        if self.params["feature"]["similarityRatio"].value == 1:
            # override the match similarity if projectin-based similarity is preferred
            self.imglog.similarities[-1] = ransac_similarity
        log.log(0, "%s\\%s -> %f", len(true_matches), len(mnkp), ransac_similarity)
        self.imglog.locations.extend(projected)

        return projected

    def log(self, lvl):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        # below selected logging level
        if lvl < self.imglog.logging_level:
            return
        # logging is being collected for a specific logtype
        elif ImageLogger.accumulate_logging:
            return
        # no hotmaps to log
        elif len(self.imglog.hotmaps) == 0:
            raise MissingHotmapError("No matching was performed in order to be image logged")

        stages = ["detect", "match", "project", ""]
        for i, stage in enumerate(stages):
            if self.imglog.logging_level > 10 and stage in ["detect", "match"]:
                continue
            if self.imglog.logging_level > 20 and stage == "project":
                continue
            if stage == "":
                name = "imglog%s-3hotmap-%s.png" % (self.imglog.printable_step,
                                                    self.imglog.similarities[-1])
            else:
                name = "imglog%s-3hotmap-%s%s.png" % (self.imglog.printable_step,
                                                      i+1, stage)
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[i])

        self.imglog.clear()
        ImageLogger.step += 1

    def _log_features(self, lvl, locations, hotmap, radius=0, r=255, g=255, b=255):
        if lvl < self.imglog.logging_level:
            return
        import cv2
        for loc in locations:
            x, y = loc
            cv2.circle(hotmap, (int(x), int(y)), radius, (r, g, b))


class CascadeMatcher(ImageFinder):
    """
    Cascade matching backend provided by OpenCV.

    This matcher uses Haar cascade for object detection.
    It is the most advanced method for object detection
    excluding convolutional neural networks. However, it
    requires the generation of a Haar cascade (if such is
    not already provided) of the needle to be found.

    TODO: Currently no similarity requirement can be applied
    due to the cascade classifier API.
    """

    def __init__(self, classifier_datapath=".", configure=True, synchronize=True):
        """Build a CV backend using OpenCV's cascade matching options."""
        super(CascadeMatcher, self).__init__(configure=False, synchronize=False)

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="cascade", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if category != "cascade":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(CascadeMatcher, self).configure_backend("cascade", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        self.params[category]["scaleFactor"] = CVParameter(1.1)
        self.params[category]["minNeighbors"] = CVParameter(3, 0, None)
        self.params[category]["minWidth"] = CVParameter(0, 0, None)
        self.params[category]["maxWidth"] = CVParameter(1000, 0, None)
        self.params[category]["minHeight"] = CVParameter(0, 0, None)
        self.params[category]["maxHeight"] = CVParameter(1000, 0, None)

    def configure_backend(self, backend=None, category="cascade", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        :param needle: target pattern (cascade) to search for
        :type needle: :py:class:`Pattern`

        See base method for details.
        """
        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        import cv2
        import numpy
        needle_cascade = cv2.CascadeClassifier(needle.data_file)
        if needle_cascade.empty():
            raise Exception("Could not load the cascade classifier properly")
        gray_haystack = cv2.cvtColor(numpy.array(haystack.pil_image), cv2.COLOR_RGB2GRAY)
        canvas = numpy.array(haystack.pil_image)

        locations = []
        rects = needle_cascade.detectMultiScale(gray_haystack,
                                                self.params["cascade"]["scaleFactor"].value,
                                                self.params["cascade"]["minNeighbors"].value,
                                                0,
                                                (self.params["cascade"]["minWidth"].value,
                                                 self.params["cascade"]["minHeight"].value),
                                                (self.params["cascade"]["maxWidth"].value,
                                                 self.params["cascade"]["maxHeight"].value))
        for (x,y,w,h) in rects:
            cv2.rectangle(canvas, (x,y), (x+w,y+h), (0, 0, 0), 2)
            cv2.rectangle(canvas, (x,y), (x+w,y+h), (255, 0, 0), 1)
            locations.append(Location(x,y))

        self.imglog.similarities.append(self.params["find"]["similarity"].value)
        self.imglog.locations = [(l.x,l.y) for l in locations]
        self.imglog.hotmaps.append(canvas)
        self.imglog.log(30)
        return locations


class HybridMatcher(TemplateMatcher, FeatureMatcher):
    """
    Hybrid matcher using both OpenCV's template and feature matching.

    Feature matching is robust at small regions not too abundant
    of features where template matching is too picky. Template
    matching is good at large feature abundant regions and can be
    used as a heuristic for the feature matching. The current matcher
    will perform template matching first and then feature matching on
    the survived template matches to select among them one more time.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's template and feature matching."""
        super(HybridMatcher, self).__init__(configure=False, synchronize=False)

        self.categories["hybrid"] = "hybrid_matchers"
        self.algorithms["hybrid_matchers"] = ("mixed",)

        if configure:
            self.__configure(reset=True)
        if synchronize:
            FeatureMatcher.synchronize(self, reset=False)

    def __configure_backend(self, backend=None, category="hybrid", reset=False):
        if category not in ["hybrid", "template", "feature", "fdetect", "fextract", "fmatch"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        elif category in ["feature", "fdetect", "fextract", "fmatch"]:
            FeatureMatcher.configure_backend(self, backend, category, reset)
            return
        elif category == "template":
            TemplateMatcher.configure_backend(self, backend, category, reset)
            return

        if reset:
            ImageFinder.configure_backend(self, "hybrid", reset=True)
        if backend is None:
            backend = "mixed"
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        self.params[category] = {}
        self.params[category]["backend"] = backend
        self.params[category]["front_similarity"] = CVParameter(0.7, 0.0, 1.0, 0.1, 0.1)

    def configure_backend(self, backend=None, category="hybrid", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __configure(self, template_match=None, feature_detect=None,
                  feature_extract=None, feature_match=None, reset=True):
        self.__configure_backend(category="hybrid", reset=reset)
        self.__configure_backend(template_match, "template")
        self.__configure_backend(category="feature")
        self.__configure_backend(feature_detect, "fdetect")
        self.__configure_backend(feature_extract, "fextract")
        self.__configure_backend(feature_match, "fmatch")

    def configure(self, template_match=None, feature_detect=None,
                  feature_extract=None, feature_match=None, reset=True):
        """
        Custom implementation of the base methods.

        See base methods for details.
        """
        self.__configure(template_match, feature_detect, feature_extract, feature_match, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        See base method for details.

        Use template matching to deal with feature dense regions
        and guide a final feature matching stage.
        """
        # accumulate one template and multiple feature cases
        ImageLogger.accumulate_logging = True

        # use a different lower similarity for the template matching
        template_similarity = self.params["hybrid"]["front_similarity"].value
        feature_similarity = self.params["find"]["similarity"].value
        log.debug("Using hybrid matching with template similarity %s "
                  "and feature similarity %s", template_similarity,
                  feature_similarity)

        # class-specific dependencies
        import cv2
        import numpy

        self.params["find"]["similarity"].value = template_similarity
        # call specifically the template find variant here
        template_maxima = TemplateMatcher.find(self, needle, haystack, True)

        self.params["find"]["similarity"].value = feature_similarity
        ngray = cv2.cvtColor(numpy.array(needle.pil_image), cv2.COLOR_RGB2GRAY)
        hgray = cv2.cvtColor(numpy.array(haystack.pil_image), cv2.COLOR_RGB2GRAY)
        final_hotmap = numpy.array(haystack.pil_image)

        frame_points = [(0, 0)]
        feature_maxima = []
        is_feature_poor = False
        for i, upleft in enumerate(template_maxima):
            up = upleft.y
            down = min(haystack.height, up + needle.height)
            left = upleft.x
            right = min(haystack.width, left + needle.width)
            log.log(0, "Maximum up-down is %s and left-right is %s",
                    (up, down), (left, right))

            haystack_region = hgray[up:down, left:right]
            haystack_region = haystack_region.copy()
            hotmap_region = final_hotmap[up:down, left:right]
            hotmap_region = hotmap_region.copy()
            # four smaller hotmaps for the feature matching stages (draw on same image here)
            self.imglog.hotmaps.append(hotmap_region)
            self.imglog.hotmaps.append(hotmap_region)
            self.imglog.hotmaps.append(hotmap_region)
            self.imglog.hotmaps.append(hotmap_region)

            res = self._project_features(frame_points, ngray, haystack_region, feature_similarity)
            # if the feature matching succeeded or is worse than satisfactory template matching
            if res != None or (self.imglog.similarities[-1] > 0.0 and
                               self.imglog.similarities[-1] < self.imglog.similarities[i] and
                               self.imglog.similarities[i] > feature_similarity):
                # take the template matching location rather than the feature one
                # for stability (they should ultimately be the same)
                location = (left, up)
                self.imglog.locations[-1] = location

                feature_maxima.append([self.imglog.hotmaps[-1],
                                       self.imglog.similarities[-1],
                                       self.imglog.locations[-1]])
                # stitch back for a better final image logging
                final_hotmap[up:down, left:right] = hotmap_region

            # if similarity is not zero but we have no result, we failed the comparison
            elif self.imglog.similarities[-1] == 0.0:
                is_feature_poor = True

        # if at least one match is feature poor, we cannot rely on feature matching
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
                if self.imglog.similarities[i] >= feature_similarity:
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
                self.imglog.hotmaps.append(final_hotmap)
                self.imglog.similarities.append(self.imglog.similarities[len(template_maxima)])
                self.imglog.locations.append(self.imglog.locations[len(template_maxima)])
            self.imglog.log(30)
            return []

        locations = []
        for maximum in feature_maxima:
            x, y = maximum[2]
            cv2.rectangle(final_hotmap, (x,y), (x+needle.width,y+needle.height), (0,0,0), 2)
            cv2.rectangle(final_hotmap, (x,y), (x+needle.width,y+needle.height), (0,0,255), 1)
            locations.append(Location(x, y))
        self.imglog.hotmaps.append(final_hotmap)
        # log one best match for final hotmap filename
        best_acceptable = max(feature_maxima, key=lambda x: x[1])
        self.imglog.similarities.append(best_acceptable[1])
        self.imglog.locations.append(best_acceptable[2])
        self.imglog.log(30)
        return locations

    def log(self, lvl):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        # below selected logging level
        if lvl < self.imglog.logging_level:
            return
        # logging is being collected for a specific logtype
        elif ImageLogger.accumulate_logging:
            return
        # no hotmaps to log
        elif len(self.imglog.hotmaps) == 0:
            raise MissingHotmapError("No matching was performed in order to be image logged")

        # knowing how the hybrid works this estimates
        # the expected number of cases starting from 1 (i+1)
        # to make sure the winner is the first alphabetically
        candidate_num = len(self.imglog.similarities) / 2
        for i in range(candidate_num):
            name = "imglog%s-3hotmap-hybrid-%stemplate-%s.png" % (self.imglog.printable_step,
                                                                  i + 1, self.imglog.similarities[i])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[i])
            ii = candidate_num + i
            hii = candidate_num + i*4 + 3
            #self.imglog.log_locations(30, [self.imglog.locations[ii]], self.imglog.hotmaps[hii], 4, 255, 0, 0)
            name = "imglog%s-3hotmap-hybrid-%sfeature-%s.png" % (self.imglog.printable_step,
                                                                 i + 1, self.imglog.similarities[ii])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[hii])

        if len(self.imglog.similarities) % 2 == 1:
            name = "imglog%s-3hotmap-hybrid-%s.png" % (self.imglog.printable_step,
                                                       self.imglog.similarities[-1])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class Hybrid2to1Matcher(HybridMatcher):
    """
    Hybrid matcher using both OpenCV's template and feature matching.

    Two thirds feature matching and one third template matching.
    Divide the haystack into x,y subregions and perform feature
    matching once for each dx,dy translation of each subregion.

    .. warning:: This matcher is currently not supported by our configuration.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's template and feature matching."""
        super(Hybrid2to1Matcher, self).__init__(configure=False, synchronize=False)

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure(self, template_match=None, feature_detect=None,
                  feature_extract=None, feature_match=None, reset=True):
        super(Hybrid2to1Matcher, self).configure(template_match, feature_detect,
                                                 feature_extract, feature_match,
                                                 reset=reset)
        self.__configure_backend(category="hybrid2to1", reset=False)

    def configure(self, template_match=None, feature_detect=None,
                  feature_extract=None, feature_match=None, reset=True):
        """
        Custom implementation of the base methods.

        See base methods for details.
        """
        self.__configure(template_match, feature_detect, feature_extract, feature_match, reset)

    def __configure_backend(self, backend=None, category="hybrid2to1", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if category != "hybrid2to1":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(Hybrid2to1Matcher, self).configure_backend("hybrid2to1", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        self.params[category]["x"] = CVParameter(1000, 1, None)
        self.params[category]["y"] = CVParameter(1000, 1, None)
        self.params[category]["dx"] = CVParameter(100, 1, None)
        self.params[category]["dy"] = CVParameter(100, 1, None)

    def configure_backend(self, backend=None, category="hybrid2to1", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        See base method for details.

        .. warning:: If this search is intensive (you use small frequent
            subregions) please disable or reduce the image logging.

        .. todo:: Currently this method is dangerous due to a possible
            memory leak. Therefore avoid getting closer to a more normal
            template matching or any small size and delta (x,y and dx,dy) that
            will cause too many match attempts.

        Example for normal template matching::

            find_2to1hybrid(n, h, s, n.width, n.height, 1, 1)

        Example to divide the screen into four quadrants and jump with distance
        halves of these quadrants::

            find_2to1hybrid(n, h, s, h.width/2, h.height/2, h.width/4, h.height/4)
        """
        # accumulate one template and multiple feature cases
        ImageLogger.accumulate_logging = True

        x = self.params["find"]["x"].value
        y = self.params["find"]["y"].value
        dx = self.params["find"]["dx"].value
        dy = self.params["find"]["dy"].value
        log.debug("Using 2to1 hybrid matching with x:%s y:%s, dx:%s, dy:%s",
                  x, y, dx, dy)

        import cv2
        import numpy
        ngray = cv2.cvtColor(numpy.array(needle.pil_image), cv2.COLOR_RGB2GRAY)
        hgray = cv2.cvtColor(numpy.array(haystack.pil_image), cv2.COLOR_RGB2GRAY)
        hcanvas = numpy.array(haystack.pil_image)

        frame_points = []
        frame_points.append((needle.width / 2, needle.height / 2))
        frame_points.extend([(0, 0), (needle.width, 0), (0, needle.height),
                             (needle.width, needle.height)])

        # the translation distance cannot be larger than the haystack
        dx = min(dx, haystack.width)
        dy = min(dy, haystack.height)
        import math
        nx = int(math.ceil(float(max(haystack.width - x, 0)) / dx) + 1)
        ny = int(math.ceil(float(max(haystack.height - y, 0)) / dy) + 1)
        log.debug("Dividing haystack into %ix%i pieces", nx, ny)
        result = numpy.zeros((ny, nx))

        locations = {}
        locations_flat = []
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
                                             self.params["find"]["similarity"].value,
                                             hotmap_region)
                result[j][i] = self.imglog.similarities[-1]

                if res is None:
                    log.debug("No acceptable match in region %s", (i, j))
                    continue
                else:
                    locations[(j, i)] = Location(left + self.imglog.locations[-1][0],
                                                 up + self.imglog.locations[-1][1])
                    locations_flat.append(locations[(j, i)])
                    self.imglog.locations[-1] = locations[(j, i)]
                    log.debug("Acceptable best match with similarity %s starting at %s in region %s",
                              self.imglog.similarities[-1], locations[(j, i)], (i, j))

        # release the accumulated logging from subroutines
        ImageLogger.accumulate_logging = False
        self.imglog.log(30)
        return locations_flat

    def log(self, lvl):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        # below selected logging level
        if lvl < self.imglog.logging_level:
            return
        # logging is being collected for a specific logtype
        elif ImageLogger.accumulate_logging:
            return
        # no hotmaps to log
        elif len(self.imglog.hotmaps) == 0:
            raise MissingHotmapError("No matching was performed in order to be image logged")

        for i in range(len(self.imglog.hotmaps)):
            name = "imglog%s-3hotmap-2to1-subregion%s-%s.png" % (self.imglog.printable_step,
                                                                 i, self.imglog.similarities[i])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[i])

        self.imglog.clear()
        ImageLogger.step += 1


class CustomMatcher(ImageFinder):
    """
    Custom matching backend with in-house CV algorithms.

    .. warning:: This matcher is currently not supported by our configuration.

    .. todo:: "in-house-raw" performs regular knn matching, but "in-house-region"
        performs a special filtering and replacement of matches based on
        positional information (it does not have ratio and symmetry tests
        and assumes that the needle is transformed preserving the relative
        positions of each pair of matches, i.e. no rotation is allowed,
        but scaling for example is supported)
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using custom matching."""
        super(CustomMatcher, self).__init__(self, configure=False, synchronize=False)

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="custom", reset=False):
        if category != "custom":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(CustomMatcher, self).configure_backend("custom", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(self, backend=None, category="custom", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack, multiple=False):
        """
        Custom implementation of the base method.

        See base method for details.

        .. todo:: This custom feature matching backend needs more serious reworking
                  before it even makes sense to get properly documented.
        """
        raise NotImplementedError("No custom matcher is currently implemented completely")

    def detect_features(self, needle, haystack):
        """
        In-house feature detection algorithm.

        :param needle: image to look for
        :type needle: :py:class:`image.Image`
        :param haystack: image to look in
        :type haystack: :py:class:`image.Image`

        .. warning:: This method is currently not fully implemented. The current
                     MSER might not be used in the actual implementation.
        """
        import cv2
        import numpy
        opencv_haystack = numpy.array(haystack.pil_image)
        opencv_needle = numpy.array(needle.pil_image)
        hgray = cv2.cvtColor(numpy.array(haystack.pil_image), cv2.COLOR_RGB2GRAY)
        ngray = cv2.cvtColor(numpy.array(needle.pil_image), cv2.COLOR_RGB2GRAY)

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

    def regionMatch(self, desc1, desc2, kp1, kp2,
                    refinements=50, recalc_interval=10,
                    variants_k=100, variants_ratio=0.33):
        """
        Use location information to better decide on matched features.

        :param desc1: descriptors of the first image
        :param desc2: descriptors of the second image
        :param kp1: key points of the first image
        :param kp2: key points of the second image
        :param int refinements: number of points to relocate
        :param int recalc_interval: recalculation on a number of refinements
        :param int variants_k: kNN parameter for to limit the alternative variants of a badly positioned feature
        :param float variants_ratio: internal ratio test for knnMatch autostop (see below)
        :returns: obtained matches

        The knn distance is now only a heuristic for the search of best
        matched set as is information on relative location with regard
        to the other matches.

        .. todo:: handle a subset of matches (ignoring some matches if not all features are detected)
        .. todo:: disable kernel mapping (multiple needle feature mapped to a single haystack feature)
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
        Performs k-Nearest Neighbor matching.

        :param desc1: descriptors of the first image
        :param desc2: descriptors of the second image
        :param int k: categorization up to k-th nearest neighbor
        :param int desc4kp: legacy parameter for the old SURF() feature detector where
                            desc4kp = len(desc2) / len(kp2) or analogically len(desc1) / len(kp1)
                            i.e. needle row 5 is a descriptor vector for needle keypoint 5
        :param float autostop: stop automatically if the ratio (dist to k)/(dist to k+1)
                               is close to 0, i.e. the k+1-th neighbor is too far.
        :returns: obtained matches
        """
        import cv2
        import numpy
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


class ImageSetFinder(ImageFinder):
    """
    Match one of a set of images usually representing the same thing.

    This matcher can work with any other matcher in the background.
    What it will do is provide with alternatives if a match fails.

    .. note:: This only works with matchers using image targets.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build an image set finder."""
        super(ImageSetFinder, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["set"] = "set_find_methods"
        self.algorithms["set_find_methods"] = ("autopy", "contour", "template", "feature", "hybrid")

        # other attributes
        self._matcher = None

        # additional preparation
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def __configure_backend(self, backend=None, category="set", reset=False):
        if category != "set":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            # backends are the same as the ones for the base class
            super(ImageSetFinder, self).configure_backend(backend=backend, reset=True)
        if backend is None:
            backend = GlobalSettings.find_image_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        self.params[category] = {}
        self.params[category]["backend"] = backend

    def configure_backend(self, backend=None, category="set", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="set", reset=False):
        if category != "set":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            # backends are the same as the ones for the base class
            super(ImageSetFinder, self).synchronize_backend(backend, reset=True)
        if backend is None:
            backend = GlobalSettings.find_image_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

        # this matcher will only work with image-based matchers
        if backend == "autopy":
            self._matcher = AutoPyMatcher()
        elif backend == "contour":
            self._matcher = ContourMatcher()
        elif backend == "template":
            self._matcher = TemplateMatcher()
        elif backend == "feature":
            self._matcher = FeatureMatcher()
        elif backend == "hybrid":
            self._matcher = HybridMatcher()

    def synchronize_backend(self, backend=None, category="set", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        See base method for details.

        .. todo:: This hasn't been fully integrated yet.
        """
        for image in needle:
            matches = self._matcher.find(image, haystack)
            if len(matches) > 0:
                return matches
        return []
