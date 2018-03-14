# Copyright 2013-2018 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import re
import copy
import random
try:
    import configparser as config
except ImportError:
    import ConfigParser as config

from config import GlobalConfig, LocalConfig
from imagelogger import ImageLogger
from path import Path
from errors import *

import logging
log = logging.getLogger('guibot.finder')


class CVParameter(object):
    """A class for a single parameter used for CV backend configuration."""

    def __init__(self, value,
                 min_val=None, max_val=None,
                 delta=10.0, tolerance=1.0,
                 fixed=True, enumerated=False):
        """
        Build a computer vision parameter.

        :param value: value of the parameter
        :type value: bool or int or float or str or None
        :param min_val: lower boundary for the parameter range
        :type min_val: int or float or None
        :param max_val: upper boundary for the parameter range
        :type max_val: int or float or None
        :param float delta: delta for the calibration and random value
                            (no calibration if `delta` < `tolerance`)
        :param float tolerance: tolerance of calibration
        :param bool fixed: whether the parameter is prevented from calibration
        :param bool enumerated: whether the parameter value belongs to an
                                enumeration or to a range (distance matters)

        As a rule of thumb a good choice for the parameter delta is one fourth
        of the range since the delta will be used as standard deviation when
        generating a random value for the parameter from a normal distribution.
        The delta to tolerance ratio is basically the number of failing trials
        before the parameter converges and is usually set to ten.
        """
        self.value = value

        # initial (delta) and minimal (tolerance) variation step
        self.delta = delta
        self.tolerance = tolerance

        # variation allowance range
        self.min_val = min_val
        if min_val is not None:
            assert value >= min_val
        elif type(self.value) == float:
            min_val = -sys.float_info.max
        elif type(self.value) == int:
            min_val = -sys.maxint
        self.max_val = max_val
        if max_val is not None:
            assert value <= max_val
        elif type(self.value) == float:
            max_val = sys.float_info.max
        elif type(self.value) == int:
            max_val = sys.maxint
        self.range = (min_val, max_val)

        # fixed or allowed to be calibrated
        self.fixed = fixed
        # enumerable (e.g. modes) or range value
        self.enumerated = enumerated
        if self.enumerated and (self.min_val is None or self.max_val is None):
            raise ValueError("Enumerated parameters must have a finite (usually small) range")

    def __repr__(self):
        """
        Provide a representation of the parameter for storing and reporting.

        :returns: special syntax representation of the parameter
        :rtype: str
        """
        return ("<value='%s' min='%s' max='%s' delta='%s' tolerance='%s' fixed='%s' enumerated='%s'>"
                % (self.value, self.min_val, self.max_val, self.delta, self.tolerance, self.fixed, self.enumerated))

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
                               r" delta='([\d.]+)' tolerance='([\d.]+)' fixed='(\w+)' enumerated='(\w+)'>",
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

            log.log(9, "%s %s", arg, type(arg))
            args.append(arg)

        log.log(9, "%s", args)
        return CVParameter(*args)

    def random_value(self, mu=None, sigma=None):
        """
        Return a random value of the CV parameter given its range and type.

        :param mu: mean for a normal distribution, uniform distribution if None
        :type mu: bool or int or float or str or None
        :param sigma: standard deviation for a normal distribution, quarter range if None
                      (maximal range is equivalent to maximal data type values)
        :type sigma: bool or int or float or str or None
        :returns: a random value comforming to the CV parameter range and type
        :rtype: bool or int or float or str or None

        .. note:: Only uniform distribution is used for boolean values.
        """
        start, end = self.range[0], self.range[1]
        if type(self.value) == float:
            if mu is None or self.enumerated:
                return random.uniform(self.range[0], self.range[1])
            elif sigma is None:
                return min(max(random.gauss(mu, (start-end)/4), start), end)
            else:
                return min(max(random.gauss(mu, sigma), start), end)
        elif type(self.value) == int:
            if mu is None or self.enumerated:
                return random.randint(start, end)
            elif sigma is None:
                return min(max(int(random.gauss(mu, (start-end)/4)), start), end)
            else:
                return min(max(int(random.gauss(mu, sigma)), start), end)
        elif type(self.value) == bool:
            value = random.randint(0, 1)
            return value == 1
        else:
            log.warning("Cannot generate random value for CV parameters other than float, int, and bool")
            return self.value


class Finder(LocalConfig):
    """
    Base for all image matching functionality and backends.

    The image finding methods include finding one or all matches
    above the similarity defined in the configuration of each backend.

    There are many parameters that could contribute for a good match. They can
    all be manually adjusted or automatically calibrated.
    """

    @staticmethod
    def from_match_file(filename):
        """
        Read the configuration from a match file with the given filename.

        :param str filename: match filename for the configuration
        :returns: target finder with the parsed (and generated) settings
        :rtype: :py:class:`finder.Finder`
        :raises: :py:class:`IOError` if the respective match file couldn't be read

        The influence of the read configuration is that of an overwrite, i.e.
        all parameters will be generated (if not already present) and then the
        ones read from the configuration file will be overwritten.
        """
        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        if not filename.endswith(".match"):
            filename += ".match"
        if not os.path.exists(filename):
            filename = Path().search(filename)
        success = parser.read(filename)
        # if no file is found throw an exception
        if len(success) == 0:
            raise IOError("Match file %s is corrupted and cannot be read" % filename)
        if not parser.has_section("find"):
            raise IOError("No image matching configuration can be found")
        try:
            backend_name = parser.get("find", 'backend')
        except config.NoOptionError:
            backend_name = GlobalConfig.find_backend

        if backend_name == "autopy":
            finder = AutoPyFinder()
        elif backend_name == "contour":
            finder = ContourFinder()
        elif backend_name == "template":
            finder = TemplateFinder()
        elif backend_name == "feature":
            finder = FeatureFinder()
        elif backend_name == "cascade":
            finder = CascadeFinder()
        elif backend_name == "text":
            finder = TextFinder()
        elif backend_name == "tempfeat":
            finder = TemplateFeatureFinder()
        elif backend_name == "deep":
            finder = DeepFinder()
        elif backend_name == "hybrid":
            finder = HybridFinder()
        else:
            raise UnsupportedBackendError("No '%s' backend is supported" % backend_name)

        for category in finder.params.keys():
            if parser.has_section(category):
                section_backend = parser.get(category, 'backend')
                if section_backend != finder.params[category]["backend"]:
                    finder.configure_backend(backend=section_backend, category=category, reset=False)
                for option in parser.options(category):
                    if option == "backend":
                        continue
                    param_string = parser.get(category, option)
                    if isinstance(finder.params[category][option], CVParameter):
                        param = CVParameter.from_string(param_string)
                        log.log(9, "%s %s", param_string, param)
                    else:
                        param = param_string
                    finder.params[category][option] = param

        return finder

    @staticmethod
    def to_match_file(finder, filename):
        """
        Write the configuration to a match file with the given filename.

        :param finder: match configuration to save
        :type finder: :py:class:`finder.Finder`
        :param str filename: match filename for the configuration
        """
        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        sections = finder.params.keys()
        for section in sections:
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, 'backend', finder.params[section]["backend"])
            for option in finder.params[section]:
                log.log(9, "%s %s", section, option)
                parser.set(section, option, finder.params[section][option])

        if not filename.endswith(".match"):
            filename += ".match"
        with open(filename, 'w') as configfile:
            configfile.write("# IMAGE MATCH DATA\n")
            parser.write(configfile)

    def __init__(self, configure=True, synchronize=True):
        """Build a finder and its CV backend settings."""
        super(Finder, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["find"] = "find_methods"
        self.algorithms["find_methods"] = ("autopy", "contour", "template", "feature",
                                           "cascade", "text", "tempfeat", "deep", "hybrid")

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
            super(Finder, self).configure_backend(backend="cv", reset=True)
        if backend is None:
            backend = GlobalConfig.find_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(9, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend
        self.params[category]["similarity"] = CVParameter(0.8, 0.0, 1.0)
        log.log(9, "%s %s\n", category, self.params[category])

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
            super(Finder, self).synchronize_backend("cv", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)
        backend = self.params[category]["backend"]

    def synchronize_backend(self, backend=None, category="find", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

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

        for key, value in self.params[category].items():
            if not isinstance(value, CVParameter):
                continue
            # BUG: force fix parameters that have internal bugs
            if category == "fextract" and key == "bytes":
                value.fixed = True
            elif category == "fdetect" and key == "Extended":
                value.fixed = True
            else:
                value.fixed = not mark
            log.debug("Setting %s/%s to fixed=%s for calibration", category, key, value.fixed)

    def copy(self):
        acopy = type(self)(synchronize=False)
        for category in self.params.keys():
            try:
                acopy.configure_backend(self.params[category]["backend"], category)
            except UnsupportedBackendError:
                # some categories are not configurable
                pass

            for param in self.params[category].keys():
                acopy.params[category][param] = copy.deepcopy(self.params[category][param])

            try:
                acopy.synchronize_backend(self.params[category]["backend"], category)
            except UnsupportedBackendError:
                # some categories are not synchronizable
                pass

        return acopy

    def find(self, needle, haystack):
        """
        Find all needle targets in a haystack image.

        :param needle: image, text, pattern, or a list or chain of such to look for
        :type needle: :py:class:`target.Target` or [:py:class:`target.Target`]
        :param haystack: image to look in
        :type haystack: :py:class:`target.Image`
        :returns: all found matches (one in most use cases)
        :rtype: [:py:class:`match.Match`]
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


class AutoPyFinder(Finder):
    """Simple matching backend provided by AutoPy."""

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using AutoPy."""
        super(AutoPyFinder, self).__init__(configure=False, synchronize=False)

        # other attributes
        self._bitmapcache = {}

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="autopy", reset=False):
        if category != "autopy":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(AutoPyFinder, self).configure_backend(backend="autopy", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(self, backend=None, category="autopy", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        :param needle: target iamge to search for
        :type needle: :py:class:`Image`

        See base method for details.

        .. warning:: AutoPy has a bug when finding multiple matches
                     so it will currently only return a single match.
        """
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
        with NamedTemporaryFile(prefix='guibot', suffix='.png') as f:
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
            similarity = self.params["find"]["similarity"].value
            self.imglog.locations.append(coord)
            self.imglog.similarities.append(similarity)
            x, y = coord
            w, h = needle.width, needle.height
            dx, dy = needle.center_offset.x, needle.center_offset.y
            from match import Match
            matches = [Match(x, y, w, h, dx, dy, similarity)]
            from PIL import ImageDraw
            draw = ImageDraw.Draw(self.imglog.hotmaps[-1])
            draw.rectangle((x, y, x+w, y+h), outline=(0,0,255))
            del draw
        else:
            matches = []
        self.imglog.log(30)
        return matches


class ContourFinder(Finder):
    """
    Contour matching backend provided by OpenCV.

    Essentially, we will find all countours in a binary image,
    preprocessed with Gaussian blur and adaptive threshold and return
    the ones with area (size) similar to the searched image.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's contour matching."""
        super(ContourFinder, self).__init__(configure=False, synchronize=False)

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
            super(ContourFinder, self).configure_backend("contour", reset=True)
        if category == "contour" and backend is None:
            backend = "mixed"
        elif category == "threshold" and backend is None:
            backend = GlobalConfig.contour_threshold_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(9, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend

        if category == "contour":
            # 1 RETR_EXTERNAL, 2 RETR_LIST, 3 RETR_CCOMP, 4 RETR_TREE
            self.params[category]["retrievalMode"] = CVParameter(2, 1, 4, enumerated=True)
            # 1 CHAIN_APPROX_NONE, 2 CHAIN_APPROX_SIMPLE, 3 CHAIN_APPROX_TC89_L1, 4 CHAIN_APPROX_TC89_KCOS
            self.params[category]["approxMethod"] = CVParameter(2, 1, 4, enumerated=True)
            self.params[category]["minArea"] = CVParameter(0, 0, None, 100.0)
            # 1 L1 method, 2 L2 method, 3 L3 method
            self.params[category]["contoursMatch"] = CVParameter(1, 1, 3, enumerated=True)
        elif category == "threshold":
            # 1 normal, 2 median, 3 gaussian, 4 none
            self.params[category]["blurType"] = CVParameter(4, 1, 4, enumerated=True)
            self.params[category]["blurKernelSize"] = CVParameter(5, 1, None, 100.0)
            self.params[category]["blurKernelSigma"] = CVParameter(0, 0, None, 100.0)
            if backend == "normal":
                # value of the threshold since it is nonadaptive and fixed
                self.params[category]["thresholdValue"] = CVParameter(122, 0, 255, 50.0)
                self.params[category]["thresholdMax"] = CVParameter(255, 0, 255, 20.0)
                # 0 binary, 1 binar_inv, 2 trunc, 3 tozero, 4 tozero_inv, 5 mask, 6 otsu, 7 triangle
                self.params[category]["thresholdType"] = CVParameter(1, 0, 7, enumerated=True)
            elif backend == "adaptive":
                self.params[category]["thresholdMax"] = CVParameter(255, 0, 255, 20.0)
                # 0 adaptive mean threshold, 1 adaptive gaussian (weighted mean) threshold
                self.params[category]["adaptiveMethod"] = CVParameter(1, 0, 1, enumerated=True)
                # 0 normal, 1 inverted
                self.params[category]["thresholdType"] = CVParameter(1, 0, 1, enumerated=True)
                # size of the neighborhood to consider to adaptive thresholding
                self.params[category]["blockSize"] = CVParameter(11, 3, None, 200.0, 2.0)
                # constant to substract from the (weighted) calculated mean
                self.params[category]["constant"] = CVParameter(2, -255, 255, 1.0)
            elif backend == "canny":
                self.params[category]["threshold1"] = CVParameter(100.0, 0.0, None, 50.0)
                self.params[category]["threshold2"] = CVParameter(1000.0, 0.0, None, 500.0)

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

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        :param needle: target iamge to search for
        :type needle: :py:class:`Image`

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

        from match import Match
        matches = []
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
                distances[index[0][0],:] = 1.1  # like this works even for similarity 0.0
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
                needle_center_offset = (needle.center_offset.x*float(w)/nw,
                                        needle.center_offset.y*float(h)/nh)
                cv2.rectangle(self.imglog.hotmaps[-1], needle_upleft, needle_downright, (0,0,0), 2)
                cv2.rectangle(self.imglog.hotmaps[-1], needle_upleft, needle_downright, (255,255,255), 1)
                # NOTE: to extract the region of interest just do:
                # roi = thresh_haystack[y:y+h,x:x+w]
                similarity = 1.0 - average_distance
                self.imglog.similarities.append(similarity)
                self.imglog.locations.append(needle_upleft)
                matches.append(Match(needle_upleft[0], needle_upleft[1],
                                     needle_downright[0] - needle_upleft[0],
                                     needle_downright[1] - needle_upleft[1],
                                     needle_center_offset[0], needle_center_offset[1],
                                     similarity))

        self.imglog.log(30)
        return matches

    def _binarize_image(self, image, log=False):
        import cv2
        # blur first in order to avoid unwonted edges caused from noise
        blurSize = self.params["threshold"]["blurKernelSize"].value
        blurDeviation = self.params["threshold"]["blurKernelSigma"].value
        gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        if self.params["threshold"]["blurType"].value == 1:
            blur_image = cv2.blur(gray_image, (blurSize,blurSize))
        elif self.params["threshold"]["blurType"].value == 2:
            blur_image = cv2.medianBlur(gray_image, blurSize)
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

        self.imglog.dump_hotmap("imglog%s-3hotmap-1threshold.png" % self.imglog.printable_step,
                                self.imglog.hotmaps[0])
        self.imglog.dump_hotmap("imglog%s-3hotmap-2contours.png" % self.imglog.printable_step,
                                self.imglog.hotmaps[1])

        similarity = self.imglog.similarities[-1] if len(self.imglog.similarities) > 0 else 0.0
        self.imglog.dump_hotmap("imglog%s-3hotmap-%s.png" % (self.imglog.printable_step, similarity),
                                self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class TemplateFinder(Finder):
    """Template matching backend provided by OpenCV."""

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's template matching."""
        super(TemplateFinder, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["template"] = "template_matchers"
        # we only use the normalized version of "sqdiff", "ccorr", and "ccoeff"
        self.algorithms["template_matchers"] = ("sqdiff_normed", "ccorr_normed", "ccoeff_normed")

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
            super(TemplateFinder, self).configure_backend("template", reset=True)
        if backend is None:
            backend = GlobalConfig.template_match_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(9, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend
        self.params[category]["nocolor"] = CVParameter(False)
        log.log(9, "%s %s\n", category, self.params[category])

    def configure_backend(self, backend=None, category="template", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        :param needle: target iamge to search for
        :type needle: :py:class:`Image`
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
        log.debug("Performing %s template matching %s color",
                  match_template, "without" if no_color else "with")
        result = self._match_template(needle, haystack, no_color, match_template)
        if result is None:
            log.warning("OpenCV's template matching returned no result")
            return []
        # switch max and min for sqdiff and sqdiff_normed (to always look for max)
        if self.params["template"]["backend"] in ("sqdiff_normed"):
            result = 1.0 - result

        import cv2
        import numpy
        universal_hotmap = result * 255.0
        final_hotmap = numpy.array(self.imglog.haystack.pil_image)
        if self.params["template"]["nocolor"].value:
            final_hotmap = cv2.cvtColor(final_hotmap, cv2.COLOR_RGB2GRAY)

        # extract maxima once for each needle size region
        similarity = self.params["find"]["similarity"].value
        from match import Match
        matches = []
        while True:

            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
            # rectify to the [0,1] interval to avoid negative values in some methods
            maxVal = min(max(maxVal, 0.0), 1.0)
            log.debug('Next best match with value %s (similarity %s) and location (x,y) %s',
                      str(maxVal), similarity, str(maxLoc))

            if maxVal < similarity:
                if len(matches) == 0:
                    self.imglog.similarities.append(maxVal)
                    self.imglog.locations.append(maxLoc)
                    current_hotmap = numpy.copy(universal_hotmap)
                    cv2.circle(current_hotmap, (maxLoc[0],maxLoc[1]), int(30*maxVal), (255,255,255))
                    self.imglog.hotmaps.append(current_hotmap)
                    self.imglog.hotmaps.append(final_hotmap)

                log.debug("Next best match is not acceptable")
                break
            else:
                self.imglog.similarities.append(maxVal)
                self.imglog.locations.append(maxLoc)
                current_hotmap = numpy.copy(universal_hotmap)
                cv2.circle(current_hotmap, (maxLoc[0],maxLoc[1]), int(30*maxVal), (255,255,255))
                x, y = maxLoc
                w, h = needle.width, needle.height
                dx, dy = needle.center_offset.x, needle.center_offset.y
                cv2.rectangle(final_hotmap, (x, y), (x+w, y+h), (0,0,0), 2)
                cv2.rectangle(final_hotmap, (x, y), (x+w, y+h), (255,255,255), 1)
                self.imglog.hotmaps.append(current_hotmap)
                log.debug("Next best match is acceptable")
                matches.append(Match(x, y, w, h, dx, dy, maxVal))
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
            log.log(9, "Wipe image matches in x [%s, %s]/[%s, %s]",
                    match_x0, match_x1, 0, res_w)
            log.log(9, "Wipe image matches in y [%s, %s]/[%s, %s]",
                    match_y0, match_y1, 0, res_h)

            # clean found image to look for next safe distance match
            result[match_y0:match_y1,match_x0:match_x1] = 0.0

            log.log(9, "Total maxima up to the point are %i", len(matches))
        log.debug("A total of %i matches found", len(matches))
        self.imglog.hotmaps.append(final_hotmap)
        self.imglog.log(30)

        return matches

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
            name = "imglog%s-3hotmap-%stemplate-%s.png" % (self.imglog.printable_step,
                                                           i + 1, self.imglog.similarities[i])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[i])

        similarity = self.imglog.similarities[-1] if len(self.imglog.similarities) > 0 else 0.0
        self.imglog.dump_hotmap("imglog%s-3hotmap-%s.png" % (self.imglog.printable_step, similarity),
                                self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class FeatureFinder(Finder):
    """
    Feature matching backend provided by OpenCV.

    .. note:: SURF and SIFT are proprietary algorithms and are not available
        by default in newer OpenCV versions (>3.0).
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's feature matching."""
        super(FeatureFinder, self).__init__(configure=False, synchronize=False)

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
                                                 "SimpleBlobDetector")
        # TODO: we could also support "StereoSGBM" but it needs initialization arguments
        # BUG: "KAZE", "AKAZE" we get internal error when using KAZE/AKAZE even though it should be possible
        self.algorithms["feature_extractors"] = ("ORB", "BRISK")

        # other attributes
        self.detector = None
        self.extractor = None
        self.matcher = None

        # additional preparation
        if configure:
            self.__configure(reset=True)
        if synchronize:
            self.__synchronize(reset=False)

    def __configure_backend(self, backend=None, category="feature", reset=False):
        if category not in ["feature", "fdetect", "fextract", "fmatch"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(FeatureFinder, self).configure_backend("feature", reset=True)
        if category == "feature" and backend is None:
            backend = "mixed"
        elif category == "fdetect" and backend is None:
            backend = GlobalConfig.feature_detect_backend
        elif category == "fextract" and backend is None:
            backend = GlobalConfig.feature_extract_backend
        elif category == "fmatch" and backend is None:
            backend = GlobalConfig.feature_match_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(9, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend

        if category == "feature":
            # 0 for homography, 1 for fundamental matrix
            self.params[category]["projectionMethod"] = CVParameter(0, 0, 1, enumerated=True)
            self.params[category]["ransacReprojThreshold"] = CVParameter(0.0, 0.0, 200.0, 50.0)
            self.params[category]["minDetectedFeatures"] = CVParameter(4, 1, None)
            self.params[category]["minMatchedFeatures"] = CVParameter(4, 1, None)
            # 0 for matched/detected ratio, 1 for projected/matched ratio
            self.params[category]["similarityRatio"] = CVParameter(1, 0, 1, enumerated=True)
        elif category == "fdetect":
            self.params[category]["nzoom"] = CVParameter(1.0, 1.0, 10.0, 2.5)
            self.params[category]["hzoom"] = CVParameter(1.0, 1.0, 10.0, 2.5)

            import cv2
            feature_detector_create = getattr(cv2, "%s_create" % backend)
            backend_obj = feature_detector_create()

        elif category == "fextract":
            import cv2
            descriptor_extractor_create = getattr(cv2, "%s_create" % backend)
            backend_obj = descriptor_extractor_create()

        elif category == "fmatch":
            if backend == "in-house-region":
                self.params[category]["refinements"] = CVParameter(50, 1, None)
                self.params[category]["recalc_interval"] = CVParameter(10, 1, None)
                self.params[category]["variants_k"] = CVParameter(100, 1, None)
                self.params[category]["variants_ratio"] = CVParameter(0.33, 0.0001, 1.0, 0.25)
                return
            else:
                self.params[category]["ratioThreshold"] = CVParameter(0.65, 0.0, 1.0, 0.25, 0.01)
                self.params[category]["ratioTest"] = CVParameter(False)
                self.params[category]["symmetryTest"] = CVParameter(False)

                # no other parameters are used for the in-house-raw matching
                if backend == "in-house-raw":
                    return
                else:

                    import cv2
                    # NOTE: descriptor matcher creation is kept the old way while feature
                    # detection and extraction not - example of the untidy maintenance of OpenCV
                    backend_obj = cv2.DescriptorMatcher_create(backend)

                    # BUG: a bug of OpenCV leads to crash if parameters
                    # are extracted from the matcher interface although
                    # the API supports it - skip fmatch for now
                    return

        # examine the interface of the OpenCV backend to add extra parameters
        if category in ["fdetect", "fextract", "fmatch"]:
            log.log(9, "%s %s", backend_obj, dir(backend_obj))
            for attribute in dir(backend_obj):
                if not attribute.startswith("get"):
                    continue
                param = attribute.replace("get", "")
                get_param = getattr(backend_obj, attribute)
                val = get_param()
                if type(val) not in [bool, int, float, type(None)]:
                    continue

                # give more information about some better known parameters
                if category in ("fdetect", "fextract") and param == "FirstLevel":
                    self.params[category][param] = CVParameter(val, 0, None, 100, 25)
                elif category in ("fdetect", "fextract") and param == "MaxFeatures":
                    self.params[category][param] = CVParameter(val, 0, None, 100.0)
                elif category in ("fdetect", "fextract") and param == "WTA_K":
                    self.params[category][param] = CVParameter(val, 2, 4, 1.0)
                elif category in ("fdetect", "fextract") and param == "ScaleFactor":
                    self.params[category][param] = CVParameter(val, 1.01, 2.0, 0.25, 0.05)
                elif category in ("fdetect", "fextract") and param == "NLevels":
                    self.params[category][param] = CVParameter(val, 1, 100, 25, 0.5)
                elif category in ("fdetect", "fextract") and param == "NLevels":
                    self.params[category][param] = CVParameter(val, 1, 100, 25, 0.5)
                elif category in ("fdetect", "fextract") and param == "PatchSize":
                    self.params[category][param] = CVParameter(val, 2, None, 100, 25)
                else:
                    self.params[category][param] = CVParameter(val)
                log.log(9, "%s=%s", param, val)

    def configure_backend(self, backend=None, category="feature", reset=False):
        """
        Custom implementation of the base method.

        Some relevant parameters are:
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
            super(FeatureFinder, self).synchronize_backend("feature", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)
        backend = self.params[category]["backend"]

        backend_obj = None
        if category == "feature":
            # nothing to sync
            return
        elif category == "fdetect":
            import cv2
            feature_detector_create = getattr(cv2, "%s_create" % backend)
            backend_obj = feature_detector_create()
        elif category == "fextract":
            import cv2
            descriptor_extractor_create = getattr(cv2, "%s_create" % backend)
            backend_obj = descriptor_extractor_create()
        elif category == "fmatch":
            import cv2
            # NOTE: descriptor matcher creation is kept the old way while feature
            # detection and extraction not - example of the untidy maintenance of OpenCV
            backend_obj = cv2.DescriptorMatcher_create(backend)
            # BUG: a bug of OpenCV leads to crash if parameters
            # are extracted from the matcher interface although
            # the API supports it - skip fmatch for now
            self.matcher = backend_obj
            return

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
                log.log(9, "Synced %s to %s", param, val)
                self.params[category][param].value = val

        if category == "fdetect":
            self.detector = backend_obj
        elif category == "fextract":
            self.extractor = backend_obj
        elif category == "fmatch":
            self.matcher = backend_obj

    def synchronize_backend(self, backend=None, category="feature", reset=False):
        """
        Custom implementation of the base method.

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

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        :param needle: target iamge to search for
        :type needle: :py:class:`Image`

        See base method for details.

        .. warning:: Finding multiple matches is currently not supported
                     and this will currently only return a single match.

        Available methods are: a combination of feature detector,
        extractor, and matcher.
        """
        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        import cv2
        import numpy
        ngray = cv2.cvtColor(numpy.array(needle.pil_image), cv2.COLOR_RGB2GRAY)
        hgray = cv2.cvtColor(numpy.array(haystack.pil_image), cv2.COLOR_RGB2GRAY)
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))
        self.imglog.hotmaps.append(numpy.array(haystack.pil_image))

        # project more points for debugging purposes and image logging
        npoints = []
        npoints.extend([(0, 0), (needle.width, 0), (0, needle.height),
                        (needle.width, needle.height)])
        npoints.append((needle.width / 2, needle.height / 2))

        similarity = self.params["find"]["similarity"].value
        hpoints = self._project_features(npoints, ngray, hgray, similarity)
        if hpoints is not None and len(hpoints) > 0:
            from match import Match
            x, y = hpoints[0]
            w, h = tuple(numpy.abs(numpy.subtract(hpoints[3], hpoints[0])))
            # TODO: projecting offset requires more effort
            matches = [Match(x, y, w, h, 0, 0, self.imglog.similarities[-1])]
            self.imglog.log(30)
            return matches
        self.imglog.log(40)
        return []

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
            return None

        locations_in_haystack = self._project_locations(locations_in_needle, mnkp, mhkp)
        if self.imglog.similarities[-1] < similarity:
            log.debug("No acceptable best match after RANSAC projection: "
                      "best match similarity %s is less than required %s",
                      self.imglog.similarities[-1], similarity)
            return None
        else:
            self._log_features(30, self.imglog.locations, self.imglog.hotmaps[-1], 3, 0, 0, 255)
            return locations_in_haystack

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

        # include only methods tested for compatibility
        if (detect in self.algorithms["feature_detectors"]
              and extract in self.algorithms["feature_extractors"]):
            self.synchronize_backend(category="fdetect")
            self.synchronize_backend(category="fextract")

            # keypoints
            nkeypoints = self.detector.detect(ngray)
            hkeypoints = self.detector.detect(hgray)

            # feature vectors (descriptors)
            (nkeypoints, ndescriptors) = self.extractor.compute(ngray, nkeypoints)
            (hkeypoints, hdescriptors) = self.extractor.compute(hgray, hkeypoints)

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

            log.log(9, "Ratio test result is %i/%i", len(matches2), len(matches))
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

            log.log(9, "Symmetry test result is %i/%i", len(matches2), len(matches))
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
            matches = self.matcher.regionMatch(ndescriptors, hdescriptors,
                                               nkeypoints, hkeypoints,
                                               self.params["fmatch"]["refinements"].value,
                                               self.params["fmatch"]["recalc_interval"].value,
                                               self.params["fmatch"]["variants_k"].value,
                                               self.params["fmatch"]["variants_ratio"].value)
        else:
            if self.params["fmatch"]["ratioTest"].value:
                matches = self.matcher.knnMatch(ndescriptors, hdescriptors, 2)
                matches = ratio_test(matches)
            else:
                matches = self.matcher.knnMatch(ndescriptors, hdescriptors, 1)
                matches = [m[0] for m in matches]
            if self.params["fmatch"]["symmetryTest"].value:
                if self.params["fmatch"]["ratioTest"].value:
                    hmatches = self.matcher.knnMatch(hdescriptors, ndescriptors, 2)
                    hmatches = ratio_test(hmatches)
                else:
                    hmatches = self.matcher.knnMatch(hdescriptors, ndescriptors, 1)
                    hmatches = [hm[0] for hm in hmatches]
                matches = symmetry_test(matches, hmatches)

        # prepare final matches
        match_nkeypoints = []
        match_hkeypoints = []
        matches = sorted(matches, key=lambda x: x.distance)
        for match in matches:
            log.log(9, match.distance)
            match_nkeypoints.append(nkeypoints[match.queryIdx])
            match_hkeypoints.append(hkeypoints[match.trainIdx])

        # these matches are half the way to being good
        mhkp_locations = [mhkp.pt for mhkp in match_hkeypoints]
        self._log_features(10, mhkp_locations, self.imglog.hotmaps[-3], 2, 255, 255, 0)

        match_similarity = float(len(match_nkeypoints)) / float(len(nkeypoints))
        # update the current achieved similarity if matching similarity is used:
        # won't be updated anymore if self.params["feature"]["similarityRatio"].value == 0
        self.imglog.similarities[-1] = match_similarity
        log.log(9, "%s\\%s -> %f", len(match_nkeypoints),
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
            log.log(9, "%s %s", orig_center_wrapped.shape, H.shape)
            match_center_wrapped = cv2.perspectiveTransform(orig_center_wrapped, H)
            (mx, my) = (match_center_wrapped[0][0][0], match_center_wrapped[0][0][1])
            projected.append((int(mx), int(my)))

        ransac_similarity = float(len(true_matches)) / float(len(mnkp))
        if self.params["feature"]["similarityRatio"].value == 1:
            # override the match similarity if projectin-based similarity is preferred
            self.imglog.similarities[-1] = ransac_similarity
        log.log(9, "%s\\%s -> %f", len(true_matches), len(mnkp), ransac_similarity)
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


class CascadeFinder(Finder):
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
        super(CascadeFinder, self).__init__(configure=False, synchronize=False)

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
            super(CascadeFinder, self).configure_backend("cascade", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        self.params[category]["scaleFactor"] = CVParameter(1.1, 0.0, None, 0.1)
        self.params[category]["minNeighbors"] = CVParameter(3, 0, None, 1.0)
        self.params[category]["minWidth"] = CVParameter(0, 0, None, 100.0)
        self.params[category]["maxWidth"] = CVParameter(1000, 0, None, 100.0)
        self.params[category]["minHeight"] = CVParameter(0, 0, None, 100.0)
        self.params[category]["maxHeight"] = CVParameter(1000, 0, None, 100.0)

    def configure_backend(self, backend=None, category="cascade", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack):
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

        from match import Match
        matches = []
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
            dx, dy = needle.center_offset.x, needle.center_offset.y
            matches.append(Match(x, y, w, h, dx, dy))

        self.imglog.similarities.append(self.params["find"]["similarity"].value)
        self.imglog.locations = [(l.x,l.y) for l in matches]
        self.imglog.hotmaps.append(canvas)
        self.imglog.log(30)
        return matches


class TextFinder(ContourFinder):
    """
    Text matching backend provided by OpenCV.

    This matcher will find a text (string) needle in the haystack,
    eventually relying on Tesseract or simpler kNN-based OCR,
    using extremal regions or contours before recognition, and
    returning a match if the string is among the recognized strings
    using string metric similar to Hamming distance.

    Extremal Region Filter algorithm described in:
    Neumann L., Matas J.: Real-Time Scene Text Localization and Recognition, CVPR 2012
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's text matching options."""
        super(TextFinder, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["text"] = "text_matchers"
        self.categories["tdetect"] = "text_detectors"
        self.categories["ocr"] = "text_recognizers"
        self.categories["threshold2"] = "threshold_filters2"
        self.categories["threshold3"] = "threshold_filters3"
        self.algorithms["text_matchers"] = ("mixed",)
        self.algorithms["text_detectors"] = ("erstat", "contours", "components")
        self.algorithms["text_recognizers"] = ("tesseract", "hmm", "beamSearch")
        self.algorithms["threshold_filters2"] = tuple(self.algorithms["threshold_filters"])
        self.algorithms["threshold_filters3"] = tuple(self.algorithms["threshold_filters"])

        # other attributes
        self.erc1 = None
        self.erf1 = None
        self.erc2 = None
        self.erf2 = None
        self.ocr = None

        # additional preparation
        if configure:
            self.__configure(reset=True)
        if synchronize:
            self.__synchronize(reset=False)

    def __configure_backend(self, backend=None, category="text", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if category not in ["text", "tdetect", "ocr", "contour", "threshold", "threshold2", "threshold3"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        elif category in ["contour", "threshold"]:
            ContourFinder.configure_backend(self, backend, category, reset)
            return
        elif category in ["threshold2", "threshold3"]:
            # simply duplicate the first threshold stage configuration
            threshold1 = self.params.get("threshold", None)
            ContourFinder.configure_backend(self, backend, "threshold", reset)
            self.params[category] = self.params["threshold"]
            if threshold1 is None:
                del self.params["threshold"]
            else:
                self.params["threshold"] = threshold1
            return

        if reset:
            Finder.configure_backend(self, "text", reset=True)
        if category == "text" and backend is None:
            backend = "mixed"
        elif category == "tdetect" and backend is None:
            backend = GlobalConfig.text_detect_backend
        elif category == "ocr" and backend is None:
            backend = GlobalConfig.text_ocr_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(9, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend

        if category == "text":
            self.params[category]["datapath"] = CVParameter("misc")
        elif category == "tdetect":
            if backend == "erstat":
                self.params[category]["thresholdDelta"] = CVParameter(1, 1, 255, 50.0)
                self.params[category]["minArea"] = CVParameter(0.00025, 0.0, 1.0, 0.25, 0.001)
                self.params[category]["maxArea"] = CVParameter(0.13, 0.0, 1.0, 0.25, 0.001)
                self.params[category]["minProbability"] = CVParameter(0.4, 0.0, 1.0, 0.25, 0.01)
                self.params[category]["nonMaxSuppression"] = CVParameter(True)
                self.params[category]["minProbabilityDiff"] = CVParameter(0.1, 0.0, 1.0, 0.25, 0.01)
                self.params[category]["minProbability2"] = CVParameter(0.3, 0.0, 1.0, 0.25, 0.01)
            elif backend == "contours":
                self.params[category]["maxArea"] = CVParameter(10000, 0, None, 1000.0, 10.0)
                self.params[category]["minWidth"] = CVParameter(1, 0, None, 100.0)
                self.params[category]["maxWidth"] = CVParameter(100, 0, None, 100.0)
                self.params[category]["minHeight"] = CVParameter(1, 0, None, 100.0)
                self.params[category]["maxHeight"] = CVParameter(100, 0, None, 100.0)
                self.params[category]["minAspectRatio"] = CVParameter(0.1, 0.0, None, 10.0)
                self.params[category]["maxAspectRatio"] = CVParameter(1.5, 0.0, None, 10.0)
                self.params[category]["horizontalSpacing"] = CVParameter(10, 0, None, 10.0)
                self.params[category]["verticalVariance"] = CVParameter(10, 0, None, 10.0)
                # 0 horizontal, 1 vertical
                self.params[category]["orientation"] = CVParameter(0, 0, 1, enumerated=True)
                self.params[category]["minChars"] = CVParameter(3, 0, None, 2.0)
            elif backend == "components":
                # with equal delta and tolerance we ensure that only one failure will be
                # allowed and no intermediary values between 4 and 8 will be selected
                self.params[category]["connectivity"] = CVParameter(4, 4, 8, 4.0, 4.0)
        elif category == "ocr":
            if backend == "tesseract":
                # eng, deu, etc. (ISO 639-3)
                self.params[category]["language"] = CVParameter("eng")
                self.params[category]["char_whitelist"] = CVParameter("0123456789abcdefghijklmnopqrst"
                                                                      "uvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
                # 0 original tesseract only, 1 neural nets LSTM only, 2 both, 3 anything available
                self.params[category]["oem"] = CVParameter(3, 0, 3, enumerated=True)
                # 13 different page segmentation modes - see Tesseract API
                self.params[category]["psmode"] = CVParameter(3, 0, 13, enumerated=True)
                # 0 OCR_LEVEL_WORD, 1 OCR_LEVEL_TEXT_LINE
                self.params[category]["component_level"] = CVParameter(1, 0, 1, enumerated=True)
                # perform custom image thresholding if set to true or leave it to the OCR
                self.params[category]["binarize_text"] = CVParameter(False)
            elif backend == "hmm":
                # 1 NM 2 CNN as classifiers for hidden markov models (see OpenCV documentation)
                self.params[category]["classifier"] = CVParameter(1, 1, 2, enumerated=True)
                # 0 OCR_LEVEL_WORD
                self.params[category]["component_level"] = CVParameter(0, 0, 1, enumerated=True)
                # perform custom image thresholding if set to true or leave it to the OCR
                self.params[category]["binarize_text"] = CVParameter(True)
            else:
                # perform custom image thresholding if set to true or leave it to the OCR
                self.params[category]["binarize_text"] = CVParameter(True)
            self.params[category]["min_confidence"] = CVParameter(0, 0, 100, 25.0)
            # zoom factor for improved OCR processing due to higher resolution
            self.params[category]["zoom_factor"] = CVParameter(1.0, 1.0, 100.0, 25.0)
            # border size to wrap around text field to improve recognition rate
            self.params[category]["border_size"] = CVParameter(10, 0, 100, 25.0)
            # 0 erode, 1 dilate, 2 both, 3 none
            self.params[category]["erode_dilate"] = CVParameter(3, 0, 3, enumerated=True)
            # 0 MORPH_RECT, 1 MORPH_ELLIPSE, 2 MORPH_CROSS
            self.params[category]["ed_kernel_type"] = CVParameter(0, 0, 2, enumerated=True)
            self.params[category]["ed_kernel_width"] = CVParameter(1, 1, 1000, 250.0, 2.0)
            self.params[category]["ed_kernel_height"] = CVParameter(1, 1, 1000, 250.0, 2.0)
            # perform distance transform if ture or not if false
            self.params[category]["distance_transform"] = CVParameter(False)
            # 1 CV_DIST_L1, 2 CV_DIST_L2, 3 CV_DIST_C
            self.params[category]["dt_distance_type"] = CVParameter(1, 1, 3, enumerated=True)
            # 0 (precise) or 3x3 or 5x5 (the latest only works with Euclidean distance CV_DIST_L2)
            self.params[category]["dt_mask_size"] = CVParameter(3, 0, 5, 8.0, 2.0)

    def configure_backend(self, backend=None, category="text", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __configure(self, text_detector=None, text_recognizer=None,
                    threshold_filter=None, threshold_filter2=None,
                    threshold_filter3=None, reset=True):
        self.__configure_backend(category="text", reset=reset)
        self.__configure_backend(text_detector, "tdetect")
        self.__configure_backend(text_recognizer, "ocr")
        self.__configure_backend(category="contour")
        self.__configure_backend(threshold_filter, "threshold")
        self.__configure_backend(threshold_filter2, "threshold2")
        self.__configure_backend(threshold_filter3, "threshold3")

    def configure(self, text_detector=None, text_recognizer=None,
                  threshold_filter=None, threshold_filter2=None,
                  threshold_filter3=None, reset=True):
        """
        Custom implementation of the base method.

        :param text_detector: name of a preselected backend
        :type text_detector: str or None
        :param text_recognizer: name of a preselected backend
        :type text_recognizer: str or None
        :param threshold_filter: threshold filter for the text detection stage
        :type threshold_filter: str or None
        :param threshold_filter2: additional threshold filter for the OCR stage
        :type threshold_filter2: str or None
        :param threshold_filter3: additional threshold filter for distance transformation
        :type threshold_filter3: str or None
        """
        self.__configure(text_detector, text_recognizer,
                         threshold_filter, threshold_filter2, threshold_filter3,
                         reset)

    def __synchronize_backend(self, backend=None, category="text", reset=False):
        if category not in ["text", "tdetect", "ocr", "contour", "threshold", "threshold2", "threshold3"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            Finder.synchronize_backend(self, "text", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)
        backend = self.params[category]["backend"]

        import cv2
        datapath = self.params["text"]["datapath"].value
        if category == "text" or category in ["contour", "threshold", "threshold2"]:
            # nothing to sync
            return

        elif category == "tdetect" and backend == "erstat":
            self.erc1 = cv2.text.loadClassifierNM1(os.path.join(datapath, 'trained_classifierNM1.xml'))
            self.erf1 = cv2.text.createERFilterNM1(self.erc1,
                                                   self.params["tdetect"]["thresholdDelta"].value,
                                                   self.params["tdetect"]["minArea"].value,
                                                   self.params["tdetect"]["maxArea"].value,
                                                   self.params["tdetect"]["minProbability"].value,
                                                   self.params["tdetect"]["nonMaxSuppression"].value,
                                                   self.params["tdetect"]["minProbabilityDiff"].value)
            self.erc2 = cv2.text.loadClassifierNM2(os.path.join(datapath, 'trained_classifierNM2.xml'))
            self.erf2 = cv2.text.createERFilterNM2(self.erc2, self.params["tdetect"]["minProbability2"].value)
        elif category == "tdetect":
            # nothing to sync
            return

        elif category == "ocr":
            if backend == "tesseract":
                self.ocr = cv2.text.OCRTesseract_create(datapath,
                                                        language=self.params["ocr"]["language"].value,
                                                        char_whitelist=self.params["ocr"]["char_whitelist"].value,
                                                        oem=self.params["ocr"]["oem"].value,
                                                        psmode=self.params["ocr"]["psmode"].value)
            elif backend in ["hmm", "beamSearch"]:

                import numpy
                # vocabulary is strictly related with the XML data so remains hardcoded here
                vocabulary = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                with open(os.path.join(datapath, 'OCRHMM_transitions_table.xml')) as f:
                    transition_p_xml = f.read()
                    transition_p_data = re.search("<data>(.*)</data>",
                                                  transition_p_xml.replace("\n"," "))
                    assert transition_p_data is not None, "Corrupted transition probability data"
                transition_p = numpy.fromstring(transition_p_data.group(1).strip(), sep=' ').reshape(62,62)
                emission_p = numpy.eye(62, dtype=numpy.float64)

                if backend == "hmm":
                    classifier_data = os.path.join(datapath, 'OCRHMM_knn_model_data.xml.gz')
                    if self.params["ocr"]["classifier"].value == 1:
                        classifier = cv2.text.loadOCRHMMClassifierNM(classifier_data)
                    elif self.params["ocr"]["classifier"].value == 2:
                        classifier = cv2.text.loadOCRHMMClassifierCNN(classifier_data)
                    else:
                        raise ValueError("Invalid classifier selected for OCR - must be NM or CNN")
                    self.ocr = cv2.text.OCRHMMDecoder_create(classifier, vocabulary, transition_p, emission_p)
                else:
                    classifier_data = os.path.join(datapath, 'OCRBeamSearch_CNN_model_data.xml.gz')
                    classifier = cv2.text.loadOCRBeamSearchClassifierCNN(classifier_data)
                    self.ocr = cv2.text.OCRBeamSearchDecoder_create(classifier, vocabulary, transition_p, emission_p)
            else:
                raise ValueError("Invalid OCR backend '%s'" % backend)

    def synchronize_backend(self, backend=None, category="text", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def __synchronize(self, text_detector=None, text_recognizer=None,
                      threshold_filter=None, threshold_filter2=None,
                      threshold_filter3=None, reset=True):
        self.__synchronize_backend(category="text", reset=reset)
        self.__synchronize_backend(text_detector, "tdetect")
        self.__synchronize_backend(text_recognizer, "ocr")
        self.__synchronize_backend(category="contour")
        self.__synchronize_backend(threshold_filter, "threshold")
        self.__synchronize_backend(threshold_filter2, "threshold2")
        self.__synchronize_backend(threshold_filter3, "threshold3")

    def synchronize(self, text_detector=None, text_recognizer=None,
                    threshold_filter=None, threshold_filter2=None,
                    threshold_filter3=None, reset=True):
        """
        Custom implementation of the base method.

        :param text_detector: name of a preselected backend
        :type text_detector: str or None
        :param text_recognizer: name of a preselected backend
        :type text_recognizer: str or None
        :param threshold_filter: threshold filter for the text detection stage
        :type threshold_filter: str or None
        :param threshold_filter2: additional threshold filter for the OCR stage
        :type threshold_filter2: str or None
        :param threshold_filter3: additional threshold filter for distance transformation
        :type threshold_filter3: str or None
        """
        self.__synchronize(text_detector, text_recognizer,
                           threshold_filter, threshold_filter2, threshold_filter3,
                           reset)

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        :param needle: target text to search for
        :type needle: :py:class:`Text`

        See base method for details.
        """
        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        import cv2
        import numpy
        text_needle = needle.value
        img_haystack = numpy.array(haystack.pil_image)
        final_hotmap = numpy.array(haystack.pil_image)

        # detect characters and group them into detected text
        backend = self.params["tdetect"]["backend"]
        if backend == "erstat":
            text_regions = self._detect_text_erstat(haystack)
        elif backend == "contours":
            text_regions = self._detect_text_contours(haystack)
        elif backend == "components":
            text_regions = self._detect_text_components(haystack)
        else:
            raise UnsupportedBackendError("Unsupported text detection backend %s" % backend)

        # perform optical character recognition on the final regions
        from match import Match
        matches = []
        def binarize_step(threshold, text_img):
            if self.params["ocr"]["binarize_text"].value:
                first_threshold = self.params["threshold"]
                self.params["threshold"] = self.params[threshold]
                try:
                    text_img = self._binarize_image(text_img)
                finally:
                    self.params["threshold"] = first_threshold
                    return text_img
            else:
                return cv2.cvtColor(text_img, cv2.COLOR_RGB2GRAY)
        for text_box in text_regions:

            # main OCR preprocessing stage
            border = self.params["ocr"]["border_size"].value
            text_img = img_haystack[max(text_box[1]-border,0):min(text_box[1]+text_box[3]+border,img_haystack.shape[0]),
                                    max(text_box[0]-border,0):min(text_box[0]+text_box[2]+border,img_haystack.shape[1])]
            factor = self.params["ocr"]["zoom_factor"].value
            log.debug("Zooming x%i candidate for improved OCR processing", factor)
            text_img = cv2.resize(text_img, None, fx=factor, fy=factor)
            text_img = binarize_step("threshold2", text_img)
            if self.params["ocr"]["distance_transform"].value:
                text_img = cv2.distanceTransform(text_img,
                                                 self.params["ocr"]["dt_distance_type"].value,
                                                 self.params["ocr"]["dt_mask_size"].value)
                text_img = cv2.cvtColor(numpy.asarray(text_img, dtype='uint8'), cv2.COLOR_GRAY2RGB)
                text_img = binarize_step("threshold3", text_img)
            if self.params["ocr"]["erode_dilate"].value < 3:
                element = cv2.getStructuringElement(self.params["ocr"]["ed_kernel_type"].value,
                                                    (self.params["ocr"]["ed_kernel_width"].value,
                                                     self.params["ocr"]["ed_kernel_height"].value))
                if self.params["ocr"]["erode_dilate"].value in [0, 2]:
                    text_img = cv2.erode(text_img, element)
                if self.params["ocr"]["erode_dilate"].value in [1, 2]:
                    text_img = cv2.dilate(text_img, element)
            self.imglog.hotmaps.append(text_img)

            # BUG: we hit segfault when using the BeamSearch OCR backend so disallow it
            if self.params["ocr"]["backend"] == "beamSearch":
                raise NotImplementedError("Current version of BeamSearch segfaults so it's not yet available")
            # TODO: can't do this in python - available ony in C++
            #vector<Rect> boxes;
            #vector<string> words;
            #vector<float> confidences;
            #output = ocr.run(group_img, &boxes, &words, &confidences, cv2.text.OCR_LEVEL_WORD)
            # redirection of tesseract's streams can only be done on the file descriptor level
            # sys.stdout = open(os.devnull, 'w')
            stdout_fd = sys.stdout.fileno() if hasattr(sys.stdout, "fileno") else 1
            stderr_fd = sys.stderr.fileno() if hasattr(sys.stderr, "fileno") else 2
            null_fo = open(os.devnull, 'wb')
            with os.fdopen(os.dup(stdout_fd), 'wb') as cpout_fo:
                with os.fdopen(os.dup(stderr_fd), 'wb') as cperr_fo:
                    sys.stdout.flush()
                    sys.stderr.flush()
                    os.dup2(null_fo.fileno(), stdout_fd)
                    os.dup2(null_fo.fileno(), stderr_fd)
                    output = self.ocr.run(text_img, text_img,
                                          self.params["ocr"]["min_confidence"].value,
                                          self.params["ocr"]["component_level"].value)
                    sys.stdout.flush()
                    sys.stderr.flush()
                    os.dup2(cpout_fo.fileno(), stdout_fd)
                    os.dup2(cperr_fo.fileno(), stderr_fd)
            if self.params["ocr"]["component_level"].value == 1:
                # strip of the new line character which is never useful
                output = output.rstrip()
            log.debug("OCR output = '%s'", output)

            similarity = 1.0 - float(needle.distance_to(output)) / max(len(output), len(text_needle))
            log.debug("Similarity = '%s'", similarity)
            self.imglog.similarities.append(similarity)
            if similarity >= self.params["find"]["similarity"].value:
                log.debug("Text at (%s, %s) is acceptable", text_box[0], text_box[1])
                self.imglog.locations.append((text_box[0], text_box[1]))
                x, y, w, h = text_box
                dx, dy = needle.center_offset.x, needle.center_offset.y
                cv2.rectangle(final_hotmap, (x, y), (x+w, y+h), (0, 0, 0), 2)
                cv2.rectangle(final_hotmap, (x, y), (x+w, y+h), (255, 255, 255), 1)
                matches.append(Match(x, y, w, h, dx, dy, similarity))
        matches = sorted(matches, key=lambda x:x.similarity, reverse=True)

        self.imglog.hotmaps.append(final_hotmap)
        self.imglog.log(30)
        return matches

    def _detect_text_erstat(self, haystack):
        import cv2
        import numpy
        img = numpy.array(haystack.pil_image)
        char_canvas = numpy.array(haystack.pil_image)
        text_canvas = numpy.array(haystack.pil_image)
        self.imglog.hotmaps.append(char_canvas)
        self.imglog.hotmaps.append(text_canvas)

        # extract channels to be processed individually - B, G, R, lightness, and gradient magnitude
        channels = cv2.text.computeNMChannels(img)
        # append negative channels to detect ER- (bright regions over dark background) skipping the gradient channel
        channel_num_without_grad = len(channels)-1
        for i in range(0, channel_num_without_grad):
            channels.append(255-channels[i])

        char_regions = []
        text_regions = []
        # apply the default cascade classifier to each independent channel
        log.debug("Extracting class specific extremal regions from %s channels", len(channels))
        for i, channel in enumerate(channels):

            # one liner for "erf1.run(channel)" then "erf2.run(channel)"
            regions = cv2.text.detectRegions(channel, self.erf1, self.erf2)
            logging.debug("A total of %s possible character regions found on channel %s", len(regions), i)
            rects = [cv2.boundingRect(p.reshape(-1, 1, 2)) for p in regions]
            for rect in rects:
                cv2.rectangle(char_canvas, (rect[0],rect[1]), (rect[0]+rect[2],rect[1]+rect[3]), (0, 0, 0), 2)
                cv2.rectangle(char_canvas, (rect[0],rect[1]), (rect[0]+rect[2],rect[1]+rect[3]), (0, 0, 255), 1)

            if len(regions) == 0:
                continue

            region_groups = cv2.text.erGrouping(img, channel, [r.tolist() for r in regions])
            logging.debug("A total of %s possible text regions found on channel %s", len(region_groups), i)
            for rect in region_groups:
                cv2.rectangle(text_canvas, (rect[0],rect[1]), (rect[0]+rect[2],rect[1]+rect[3]), (0, 0, 0), 2)
                cv2.rectangle(text_canvas, (rect[0],rect[1]), (rect[0]+rect[2],rect[1]+rect[3]), (0, 255, 0), 1)

            char_regions.extend(regions)
            text_regions.extend(region_groups)

        # produce a final set of nonintersecting text regions
        final_regions = []
        region_queue = [[region, True] for region in text_regions]
        while True:
            # nothing to do for just one region
            if len(region_queue) < 2:
                break
            r1, flag1 = region_queue.pop(0)
            if not flag1:
                continue
            for r2pair in region_queue:
                r2, _ = r2pair
                # if the two regions intersect
                if (r1[0] < r2[0] + r2[2] and r1[0] + r1[2] > r2[0] and
                        r1[1] < r2[1] + r2[3] and r1[1] + r1[3] > r2[1]):
                    r1 = [min(r1[0], r2[0]), min(r1[1], r2[1]), max(r1[2], r2[2]), max(r1[3], r2[3])]
                    # second region will no longer be considered
                    r2pair[1] = False
            # first region is now merged with all intersecting regions
            final_regions.append(r1)
        return final_regions

    def _detect_text_contours(self, haystack):
        import cv2
        import numpy
        img = numpy.array(haystack.pil_image)
        char_canvas = numpy.array(haystack.pil_image)
        text_canvas = numpy.array(haystack.pil_image)
        self.imglog.hotmaps.append(char_canvas)
        self.imglog.hotmaps.append(text_canvas)

        thresh_haystack = self._binarize_image(img)
        countours_haystack = thresh_haystack.copy()
        haystack_contours = self._extract_contours(countours_haystack)

        char_regions = []
        for hcontour in haystack_contours:
            x, y, w, h = cv2.boundingRect(hcontour)
            area, ratio = cv2.contourArea(hcontour), float(w)/h
            if (area < self.params["contour"]["minArea"].value or
                area > self.params["tdetect"]["maxArea"].value or
                w < self.params["tdetect"]["minWidth"].value or
                w > self.params["tdetect"]["maxWidth"].value or
                h < self.params["tdetect"]["minHeight"].value or
                h > self.params["tdetect"]["maxHeight"].value or
                ratio < self.params["tdetect"]["minAspectRatio"].value or
                ratio > self.params["tdetect"]["maxAspectRatio"].value):
                log.debug("Ignoring contour with area %sx%s>%s and aspect ratio %s/%s=%s",
                          w, h, area, w, h, ratio)
                continue
            else:
                cv2.rectangle(char_canvas, (x,y), (x+w,y+h), (0, 0, 0), 2)
                cv2.rectangle(char_canvas, (x,y), (x+w,y+h), (0, 0, 255), 1)
                char_regions.append([x, y, w, h])
        char_regions = sorted(char_regions, key=lambda x:x[0])

        # group characters into horizontally-correlated regions
        text_regions = []
        dx, dy = self.params["tdetect"]["horizontalSpacing"].value, self.params["tdetect"]["verticalVariance"].value
        text_orientation = self.params["tdetect"]["orientation"].value
        min_chars_for_text = self.params["tdetect"]["minChars"].value
        for i, region1 in enumerate(char_regions):
            # region was already merged
            if region1 is None:
                continue
            chars_for_text = 0
            for j, region2 in enumerate(char_regions):
                # region is compared to itself or to merged region
                if region1 == region2 or region2 is None:
                    continue
                x1, y1, w1, h1 = region1
                x2, y2, w2, h2 = region2
                if text_orientation == 0:
                    is_text = x2 - (x1 + w1) < dx and x1 - (x2 + w2) < dx and abs(y1 - y2) < dy and abs(h1 - h2) < 2*dy
                elif text_orientation == 1:
                    is_text = y2 - (y1 + h1) < dy and y1 - (y2 + h2) < dy and abs(x1 - x2) < dx and abs(w1 - w2) < 2*dx
                if is_text:
                    region1 = [min(x1,x2), min(y1,y2), max(x1+w1,x2+w2)-min(x1,x2), max(y1+h1,y2+h2)-min(y1,y2)]
                    chars_for_text += 1
                    char_regions[j] = None
            if chars_for_text < min_chars_for_text:
                log.debug("Ignoring text contour with %s<%s characters",
                          chars_for_text, min_chars_for_text)
                continue
            x, y, w, h = region1
            cv2.rectangle(text_canvas, (x, y), (x+w,y+h), (0, 0, 0), 2)
            cv2.rectangle(text_canvas, (x, y), (x+w,y+h), (0, 255, 0), 1)
            text_regions.append(region1)
            char_regions[i] = None

        return text_regions

    def _detect_text_components(self, haystack):
        import cv2
        import numpy
        img = numpy.array(haystack.pil_image)
        char_canvas = numpy.array(haystack.pil_image)
        text_canvas = numpy.array(haystack.pil_image)
        self.imglog.hotmaps.append(char_canvas)
        self.imglog.hotmaps.append(text_canvas)

        connectivity = self.params["tdetect"]["connectivity"].value
        label_num, label_img, stats, centroids = cv2.connectedComponentsWithStats(img, connectivity, cv2.CV_32S)
        logging.debug("Detected %s component labels with centroids: %s", label_num,
                      ", ".join([str((int(c[0]),int(c[1]))) for c in centroids]))
        self.imglog.hotmaps.append(label_img * 255)
        for i in range(label_num):
            x, y = stats[i,cv2.CC_STAT_LEFT], stats[i,cv2.CC_STAT_TOP]
            w, h = stats[i,cv2.CC_STAT_WIDTH], stats[i,cv2.CC_STAT_HEIGHT]
            area = stats[i,cv2.CC_STAT_AREA]
            if area < self.params["contour"]["minArea"].value:
                continue
            else:
                rect = [x, y, w, h]
                cv2.rectangle(char_canvas, (rect[0],rect[1]), (rect[0]+rect[2],rect[1]+rect[3]), (0, 0, 0), 2)
                cv2.rectangle(char_canvas, (rect[0],rect[1]), (rect[0]+rect[2],rect[1]+rect[3]), (0, 0, 255), 1)

        # TODO: log here since not fully implemented
        self.imglog.hotmaps[-1] = cv2.normalize(label_img, label_img, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        self.imglog.log(30)
        raise NotImplementedError("The connected components method for text detection needs more labels")

        # TODO: alternatively use cvBlobsLib
        myblobs = CBlobResult(binary_image, mask, 0, True)
        myblobs.filter_blobs(325, 2000)
        blob_count = myblobs.GetNumBlobs()

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

        self.imglog.dump_hotmap("imglog%s-3hotmap-1char.png" % self.imglog.printable_step,
                                self.imglog.hotmaps[0])
        self.imglog.dump_hotmap("imglog%s-3hotmap-2text.png" % self.imglog.printable_step,
                                self.imglog.hotmaps[1])

        for i in range(2, len(self.imglog.hotmaps)-1):
            self.imglog.dump_hotmap("imglog%s-3hotmap-3ocr-%stext-%s.png" % (self.imglog.printable_step, i-1,
                                                                             self.imglog.similarities[i-2]),
                                    self.imglog.hotmaps[i])

        similarity = max(self.imglog.similarities) if len(self.imglog.similarities) > 0 else 0.0
        self.imglog.dump_hotmap("imglog%s-3hotmap-%s.png" % (self.imglog.printable_step, similarity),
                                self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class TemplateFeatureFinder(TemplateFinder, FeatureFinder):
    """
    Hybrid matcher using both OpenCV's template and feature matching.

    Feature matching is robust at small regions not too abundant
    of features where template matching is too picky. Template
    matching is good at large feature abundant regions and can be
    used as a heuristic for the feature matching. The current matcher
    will perform template matching first and then feature matching on
    the survived template matches to select among them one more time.

    A separate (usually lower) front similarity is used for the first
    stage template matching in order to remove a lot of noise that
    would otherwise be distracting for the second stage feature matching.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's template and feature matching."""
        super(TemplateFeatureFinder, self).__init__(configure=False, synchronize=False)

        self.categories["tempfeat"] = "tempfeat_matchers"
        self.algorithms["tempfeat_matchers"] = ("mixed",)

        if configure:
            self.__configure(reset=True)
        if synchronize:
            FeatureFinder.synchronize(self, reset=False)

    def __configure_backend(self, backend=None, category="tempfeat", reset=False):
        if category not in ["tempfeat", "template", "feature", "fdetect", "fextract", "fmatch"]:
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        elif category in ["feature", "fdetect", "fextract", "fmatch"]:
            FeatureFinder.configure_backend(self, backend, category, reset)
            return
        elif category == "template":
            TemplateFinder.configure_backend(self, backend, category, reset)
            return

        if reset:
            Finder.configure_backend(self, "tempfeat", reset=True)
        if backend is None:
            backend = "mixed"
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        self.params[category] = {}
        self.params[category]["backend"] = backend
        self.params[category]["front_similarity"] = CVParameter(0.7, 0.0, 1.0)

    def configure_backend(self, backend=None, category="tempfeat", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __configure(self, template_match=None, feature_detect=None,
                  feature_extract=None, feature_match=None, reset=True):
        self.__configure_backend(category="tempfeat", reset=reset)
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

    def synchronize(self, feature_detect=None, feature_extract=None,
                    feature_match=None, reset=True):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        Finder.synchronize_backend(self, "tempfeat", reset=reset)
        FeatureFinder.synchronize(self,
                                  feature_detect=feature_detect,
                                  feature_extract=feature_extract,
                                  feature_match=feature_match,
                                  reset=False)

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        See base method for details.

        Use template matching to deal with feature dense regions
        and guide a final feature matching stage.
        """
        # accumulate one template and multiple feature cases
        ImageLogger.accumulate_logging = True

        # use a different lower similarity for the template matching
        template_similarity = self.params["tempfeat"]["front_similarity"].value
        feature_similarity = self.params["find"]["similarity"].value
        log.debug("Using tempfeat matching with template similarity %s "
                  "and feature similarity %s", template_similarity,
                  feature_similarity)

        # class-specific dependencies
        import cv2
        import numpy

        self.params["find"]["similarity"].value = template_similarity
        # call specifically the template find variant here
        template_maxima = TemplateFinder.find(self, needle, haystack)

        self.params["find"]["similarity"].value = feature_similarity
        # dump correct matching settings
        self.imglog.dump_matched_images()
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
            log.log(9, "Maximum up-down is %s and left-right is %s",
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
                log.debug("Using template result %s instead of the worse feature result %s",
                          self.imglog.similarities[i], self.imglog.similarities[-1])
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
            if len(self.imglog.similarities) > 1:
                # NOTE: handle cases when the matching failed at the feature stage, i.e. dump
                # a hotmap for debugging also in this case
                self.imglog.hotmaps.append(final_hotmap)
                self.imglog.similarities.append(self.imglog.similarities[len(template_maxima)])
                self.imglog.locations.append(self.imglog.locations[len(template_maxima)])
            elif len(self.imglog.similarities) == 1:
                # NOTE: we are only interested in the template hotmap on template failure
                self.imglog.hotmaps.append(self.imglog.hotmaps[0])
            self.imglog.log(30)
            return []

        matches = []
        from match import Match
        maxima = sorted(feature_maxima, key=lambda x:x[1], reverse=True)
        for maximum in maxima:
            similarity = maximum[1]
            x, y = maximum[2]
            w, h = needle.width, needle.height
            dx, dy = needle.center_offset.x, needle.center_offset.y
            cv2.rectangle(final_hotmap, (x,y), (x+needle.width,y+needle.height), (0,0,0), 2)
            cv2.rectangle(final_hotmap, (x,y), (x+needle.width,y+needle.height), (0,0,255), 1)
            matches.append(Match(x, y, w, h, dx, dy, similarity))
        self.imglog.hotmaps.append(final_hotmap)
        # log one best match for final hotmap filename
        best_acceptable = maxima[0]
        self.imglog.similarities.append(best_acceptable[1])
        self.imglog.locations.append(best_acceptable[2])

        self.imglog.log(30)
        return matches

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

        # knowing how the tempfeat works this estimates
        # the expected number of cases starting from 1 (i+1)
        # to make sure the winner is the first alphabetically
        candidate_num = len(self.imglog.similarities) / 2
        for i in range(candidate_num):
            name = "imglog%s-3hotmap-%stemplate-%s.png" % (self.imglog.printable_step,
                                                           i + 1, self.imglog.similarities[i])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[i])
            ii = candidate_num + i
            hii = candidate_num + i*4 + 3
            #self.imglog.log_locations(30, [self.imglog.locations[ii]], self.imglog.hotmaps[hii], 4, 255, 0, 0)
            name = "imglog%s-3hotmap-%sfeature-%s.png" % (self.imglog.printable_step,
                                                          i + 1, self.imglog.similarities[ii])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[hii])

        if len(self.imglog.similarities) % 2 == 1:
            name = "imglog%s-3hotmap-%s.png" % (self.imglog.printable_step,
                                                self.imglog.similarities[-1])
            self.imglog.dump_hotmap(name, self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class DeepFinder(Finder):
    """
    Deep learning matching backend provided by PyTorch.

    The current implementation contains a basic convolutional
    neural network which can be trained to produce needle locations
    from a haystack image.
    """

    def __init__(self, classifier_datapath=".", configure=True, synchronize=True):
        """Build a CV backend using OpenCV's text matching options."""
        super(DeepFinder, self).__init__(configure=False, synchronize=False)

        # other attributes
        self.net = None

        # additional preparation
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def __configure_backend(self, backend=None, category="deep", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if category != "deep":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(DeepFinder, self).configure_backend("deep", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

        self.params[category]["use_cuda"] = CVParameter(False)
        self.params[category]["batch_size"] = CVParameter(1000, 0, None)
        self.params[category]["log_interval"] = CVParameter(10, 1, None)
        self.params[category]["learning_rate"] = CVParameter(0.01, 0.0, 1.0)
        self.params[category]["sgd_momentum"] = CVParameter(0.5, 0.0, 1.0)

        self.params[category]["iwidth"] = CVParameter(150, 0, None)
        self.params[category]["iheight"] = CVParameter(150, 0, None)
        self.params[category]["owidth"] = CVParameter(15, 0, None)
        self.params[category]["oheight"] = CVParameter(15, 0, None)

        self.params[category]["channels_conv1"] = CVParameter(10, 1, None)
        self.params[category]["kernel_conv1"] = CVParameter(5, 0, None)
        self.params[category]["kernel_pool1"] = CVParameter(2, 0, None)
        self.params[category]["channels_conv2"] = CVParameter(20, 1, None)
        self.params[category]["kernel_conv2"] = CVParameter(5, 0, None)
        self.params[category]["kernel_pool2"] = CVParameter(2, 0, None)
        self.params[category]["outputs_linear1"] = CVParameter(50, 0, None)

    def configure_backend(self, backend=None, category="deep", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="deep", reset=False):
        if category != "deep":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(DeepFinder, self).synchronize_backend("deep", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)
        backend = self.params[category]["backend"]

        # class-specific dependencies
        import torch.nn as nn
        import torch.nn.functional as F
        f = self

        class Net(nn.Module):
            """Nested class for convolutional neural network."""

            def __init__(self):
                super(Net, self).__init__()

                # short names for network parameters
                iw, ih = f.params["deep"]["iwidth"].value, f.params["deep"]["iheight"].value
                c1k, c1c = f.params["deep"]["kernel_conv1"].value, f.params["deep"]["channels_conv1"].value
                c2k, c2c = f.params["deep"]["kernel_conv2"].value, f.params["deep"]["channels_conv2"].value
                c1p, c2p = f.params["deep"]["kernel_pool1"].value, f.params["deep"]["kernel_pool2"].value
                ow, oh = f.params["deep"]["owidth"].value, f.params["deep"]["oheight"].value

                # calculate the number of inputs of the first linear layer
                rw = ((iw - c1k + 1) / c1p - c2k + 1) / c2p
                rh = ((ih - c1k + 1) / c1p - c2k + 1) / c2p
                n = rw * rh * c2c

                self.conv1 = nn.Conv2d(1, c1c, kernel_size=c1k)
                self.conv2 = nn.Conv2d(c1c, c2c, kernel_size=c2k)
                self.conv2_drop = nn.Dropout2d()
                self.fc1 = nn.Linear(n, f.params["deep"]["outputs_linear1"].value)
                # one extra class for no location
                self.fc2 = nn.Linear(f.params["deep"]["outputs_linear1"].value, ow * oh + 1)

            def forward(self, x):
                x = self.conv1(x)
                # max pooling with some kernel and stride downsamples using max
                x = F.max_pool2d(x, f.params["deep"]["kernel_pool1"].value)
                # rectifier linear unit (ReLu) is simply max(x,0)
                x = F.relu(x)
                # second convolutional layer
                x = self.conv2_drop(self.conv2(x))
                x = F.relu(F.max_pool2d(x, f.params["deep"]["kernel_pool2"].value))
                # rearrange to flat layer (size = inputs of first linear layer)
                x = x.view(-1, self.fc1.in_features)
                x = F.relu(self.fc1(x))
                # use dropout to avoid overfitting
                x = F.dropout(x, training=self.training)
                x = F.relu(self.fc2(x))
                # softmax gives a vector of the same dimension with components sum of 1
                x = F.log_softmax(x)
                return x

        self.net = Net()

    def synchronize_backend(self, backend=None, category="deep", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def find(self, needle, haystack):
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
        # prepare a canvas solely for image logging
        canvas = haystack.pil_image.copy()

        # load .pth or .pkl data file if pretrained model is available
        import torch
        if needle.data_file is not None:
            weights = torch.load(needle.data_file)
            self.net.load_state_dict(weights)

        # set the module in evaluation mode
        self.net.eval()

        # convert haystack data to tensor variable
        import PIL
        gray = haystack.pil_image.convert('L')
        size = (self.params["deep"]["iwidth"].value, self.params["deep"]["iheight"].value)
        gray.thumbnail(size, PIL.Image.ANTIALIAS)
        gray_bg = PIL.Image.new('L', size, (255))
        gray_bg.paste(gray,
                      (int((size[0] - gray.size[0]) / 2),
                       int((size[1] - gray.size[1]) / 2)))
        gray = gray_bg
        import numpy
        gray = numpy.array(gray,
                           dtype=numpy.float32).reshape((1, 1, # batch size and channel number
                                                         self.params["deep"]["iwidth"].value,
                                                         self.params["deep"]["iheight"].value))
        from torch.autograd import Variable
        data = Variable(torch.from_numpy(gray/255), volatile=True)

        # send input to the network and get probability distribution over locations
        output = self.net(data)
        import torch.nn.functional as F
        output = F.softmax(output)
        hotmap = output.data[...,:-1].numpy().reshape(self.params["deep"]["oheight"].value,
                                                      self.params["deep"]["owidth"].value)
        self.imglog.hotmaps.append(hotmap*255)

        # TODO: try Faster Region-CNNs, Single Shot MultiBox Detector, and YOLO
        matches = []
        from match import Match
        dx = haystack.width / self.params["deep"]["owidth"].value
        dy = haystack.height / self.params["deep"]["oheight"].value
        ys, xs = numpy.where(hotmap > self.params["find"]["similarity"].value)
        for (x, y) in zip(list(xs), list(ys)):
            similarity = hotmap[y,x]
            ox, oy = dx * x, dy * y
            ndx, ndy = needle.center_offset.x, needle.center_offset.y

            from PIL import ImageDraw
            draw = ImageDraw.Draw(canvas)
            draw.rectangle((ox, oy, ox+dx, oy+dy), outline=(0,0,255))

            self.imglog.locations.append((ox, oy))
            self.imglog.similarities.append(hotmap[y,x])
            matches.append(Match(ox, oy, dx, dy, ndx, ndy, similarity))

        self.imglog.hotmaps.append(canvas)
        self.imglog.log(30)
        return matches

    def train(self, epochs, train_samples, train_targets, data_filename=None):
        """
        Train the convolutional neural network.

        :param int epochs: number of training epochs (train on all samples for each)
        :param str train_samples: filename for the samples dataset
        :param str train_targets: filename for the targets dataset
        :param data_filename: file name for storing the trained model (won't store if None)
        :param data_filename: str or None
        """
        # create loader for the data (allowing batches and other extras)
        import torch
        data_tensor, target_tensor = torch.load(train_samples), torch.load(train_targets)
        kwargs = {'num_workers': 1, 'pin_memory': True} if self.params["deep"]["use_cuda"].value else {}
        from torch.utils.data import TensorDataset
        train_loader = torch.utils.data.DataLoader(TensorDataset(data_tensor, target_tensor),
                                                   batch_size=self.params["deep"]["batch_size"].value,
                                                   shuffle=True, **kwargs)

        # initialize stochastic gradient descent optimizer for learning
        import torch.optim as optim
        optimizer = optim.SGD(self.net.parameters(),
                              lr=self.params["deep"]["learning_rate"].value,
                              momentum=self.params["deep"]["sgd_momentum"].value)

        # set the module in training mode
        self.net.train()

        from torch.autograd import Variable
        import torch.nn.functional as F
        for epoch in range(1, epochs + 1):
            # loader iterator returns batches of samples
            for batch_idx, (data, target) in enumerate(train_loader):
                if self.params["deep"]["use_cuda"].value:
                    data, target = data.cuda(), target.cuda()
                data, target = Variable(data), Variable(target)

                # main training step
                optimizer.zero_grad()
                output = self.net(data)
                loss = F.nll_loss(output, target)

                # backpropagation happens here
                loss.backward()
                # learning happens here
                optimizer.step()

                # log measurements on each ten batches
                if batch_idx % self.params["deep"]["log_interval"].value == 0:
                    log.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                            epoch, batch_idx * len(data), len(train_loader.dataset),
                            100. * batch_idx / len(train_loader), loss.data[0]))

        # save the network state if required
        if data_filename is not None:
            state_dict = self.net.state_dict()
            log.debug("Resulting state dictionary (weights, biases, etc) of the network:\n%s", state_dict)
            torch.save(state_dict, data_filename)

    def test(self, train_samples, train_targets):
        """
        Test the convolutional neural network.

        :param str train_samples: filename for the samples dataset
        :param str train_targets: filename for the targets dataset
        """
        # create loader for the data (allowing batches and other extras)
        import torch
        data_tensor, target_tensor = torch.load(train_samples), torch.load(train_targets)
        kwargs = {'num_workers': 1, 'pin_memory': True} if self.params["deep"]["use_cuda"].value else {}
        from torch.utils.data import TensorDataset
        test_loader = torch.utils.data.DataLoader(TensorDataset(data_tensor, target_tensor),
                                                  batch_size=self.params["deep"]["batch_size"].value,
                                                  shuffle=True, **kwargs)

        # set the module in evaluation mode
        self.net.eval()

        test_loss = 0
        correct = 0
        from torch.autograd import Variable
        import torch.nn.functional as F
        # loader iterator returns batches of samples
        for data, target in test_loader:
            if self.params["deep"]["use_cuda"].value:
                data, target = data.cuda(), target.cuda()
            # volatile implies to use the variable in inference mode
            data, target = Variable(data, volatile=True), Variable(target)

            # main testing step
            output = self.net(data)
            # accumulate negative log likelihood loss
            test_loss += F.nll_loss(output, target).data[0]
            # get the index of the max log-probability
            pred = output.data.max(1)[1]
            # calculate accuracy as well
            correct += pred.eq(target.data).cpu().sum()

        # loss function already averages over batch size
        test_loss /= len(test_loader)
        # log measurements - this is the only testing action
        log.info('Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)'.format(
                test_loss, correct, len(test_loader.dataset),
                100. * correct / len(test_loader.dataset)))

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

        self.imglog.dump_hotmap("imglog%s-3hotmap-1activity.png" % self.imglog.printable_step,
                                self.imglog.hotmaps[0])

        similarity = self.imglog.similarities[-1] if len(self.imglog.similarities) > 0 else 0.0
        name = "imglog%s-3hotmap-%s.png" % (self.imglog.printable_step, similarity)
        self.imglog.dump_hotmap(name, self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class CustomFinder(Finder):
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
        super(CustomFinder, self).__init__(self, configure=False, synchronize=False)

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="custom", reset=False):
        if category != "custom":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(CustomFinder, self).configure_backend("custom", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(self, backend=None, category="custom", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack):
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
        :type needle: :py:class:`target.Image`
        :param haystack: image to look in
        :type haystack: :py:class:`target.Image`

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
            log.log(9, "%s:%s=%s", origin, target, coord)
            return coord

        def compare_pos(match1, match2):
            hc = rcoord(hcoord(match1), hcoord(match2))
            nc = rcoord(ncoord(match1), ncoord(match2))

            valid_positioning = True
            if hc[0] != nc[0] and hc[0] != 0 and nc[0] != 0:
                valid_positioning = False
            if hc[1] != nc[1] and hc[1] != 0 and nc[1] != 0:
                valid_positioning = False

            log.log(9, "p1:p2 = %s in haystack and %s in needle", hc, nc)
            log.log(9, "is their relative positioning valid? %s", valid_positioning)

            return valid_positioning

        def match_cost(matches, new_match):
            if len(matches) == 0:
                return 0.0

            nominator = sum(float(not compare_pos(match, new_match)) for match in matches)
            denominator = float(len(matches))
            ratio = nominator / denominator
            log.log(9, "model <-> match = %i disagreeing / %i total matches",
                    nominator, denominator)

            # avoid 0 mapping, i.e. giving 0 positional
            # conflict to 0 distance matches or 0 distance
            # to matches with 0 positional conflict
            if ratio == 0.0 and new_match.distance != 0.0:
                ratio = 0.001
            elif new_match.distance == 0.0 and ratio != 0.0:
                new_match.distance = 0.001

            cost = ratio * new_match.distance
            log.log(9, "would be + %f cost", cost)
            log.log(9, "match reduction: %s",
                    cost / max(sum(m.distance for m in matches), 1))

            return cost

        results = self.knnMatch(desc1, desc2, variants_k,
                                1, variants_ratio)
        matches = [variants[0] for variants in results]
        ratings = [None for _ in matches]
        log.log(9, "%i matches in needle to start with", len(matches))

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
            log.log(9, "outlier m%i with rating %i", outlier_index, max(ratings))
            log.log(9, "%i match variants for needle match %i", len(variants), outlier_index)

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
                log.log(9, "variant %i is m%i/%i in n/h", j, variant.queryIdx, variant.trainIdx)
                log.log(9, "variant %i coord in n/h %s/%s", j, ncoord(variant), hcoord(variant))
                log.log(9, "variant distance: %s", variant.distance)

                matches[outlier_index] = variant
                variant_costs.append((j, match_cost(matches, variant)))

            min_cost_index, min_cost = min(variant_costs, key=lambda x: x[1])
            min_cost_variant = variants[min_cost_index]
            # if variant_costs.index(min(variant_costs)) != 0:
            log.log(9, "%s>%s i.e. variant %s", variant_costs, min_cost, min_cost_index)
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
            log.log(9, "%s %s", desc1.shape, desc2.shape)
        else:
            desc1 = numpy.array(desc1, dtype=numpy.float32)
            desc2 = numpy.array(desc2, dtype=numpy.float32)
        desc_size = desc2.shape[1]

        # kNN training - learn mapping from rows2 to kp2 index
        samples = desc2
        responses = numpy.arange(int(len(desc2) / desc4kp), dtype=numpy.float32)
        log.log(9, "%s %s", len(samples), len(responses))
        knn = cv2.KNearest()
        knn.train(samples, responses, maxK=k)

        matches = []
        # retrieve index and value through enumeration
        for i, descriptor in enumerate(desc1):
            descriptor = numpy.array(descriptor, dtype=numpy.float32).reshape((1, desc_size))
            log.log(9, "%s %s %s", i, descriptor.shape, samples[0].shape)
            kmatches = []
            ratio = 1.0

            for ki in range(k):
                _, res, _, dists = knn.find_nearest(descriptor, ki + 1)
                log.log(9, "%s %s %s", ki, res, dists)
                if len(dists[0]) > 1 and autostop > 0.0:

                    # TODO: perhaps ratio from first to last ki?
                    # smooth to make 0/0 case also defined as 1.0
                    dist1 = dists[0][-2] + 0.0000001
                    dist2 = dists[0][-1] + 0.0000001
                    ratio = dist1 / dist2
                    log.log(9, "%s %s", ratio, autostop)
                    if ratio < autostop:
                        break

                kmatches.append(cv2.DMatch(i, int(res[0][0]), dists[0][-1]))

            matches.append(tuple(kmatches))
        return matches


class HybridFinder(Finder):
    """
    Match a target through a sequence of differently configured attempts.

    This matcher can work with any other matcher in the background and with
    unique or repeating matchers for each step. If a step fails, the matcher
    tries the next available along the fallback chain or fails if the end of
    the chain is reached.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a hybrid matcher."""
        super(HybridFinder, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["hybrid"] = "hybrid_methods"
        self.algorithms["hybrid_methods"] = ("autopy", "contour", "template", "feature", "tempfeat")

        # other attributes
        self.matcher = None

        # additional preparation
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def __configure_backend(self, backend=None, category="hybrid", reset=False):
        if category != "hybrid":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            # backends are the same as the ones for the base class
            super(HybridFinder, self).configure_backend(backend=backend, reset=True)
        if backend is None:
            backend = GlobalConfig.hybrid_match_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        self.params[category] = {}
        self.params[category]["backend"] = backend

    def configure_backend(self, backend=None, category="hybrid", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="hybrid", reset=False):
        if category != "hybrid":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(HybridFinder, self).synchronize_backend("hybrid", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)
        backend = self.params[category]["backend"]

        # default matcher in case of a simple chain without own matching config
        if backend == "autopy":
            self.matcher = AutoPyFinder()
        elif backend == "contour":
            self.matcher = ContourFinder()
        elif backend == "template":
            self.matcher = TemplateFinder()
        elif backend == "feature":
            self.matcher = FeatureFinder()
        elif backend == "cascade":
            self.matcher = CascadeFinder()
        elif backend == "text":
            self.matcher = TextFinder()
        elif backend == "tempfeat":
            self.matcher = TemplateFeatureFinder()
        elif backend == "deep":
            self.matcher = DeepFinder()

    def synchronize_backend(self, backend=None, category="hybrid", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        try:
            iter(needle)
        except TypeError:
            # one step chains can be of any target type
            log.debug("Defaulting to one step chain %s", needle)
            needle = [needle]

        for step_needle in needle:

            if step_needle.use_own_settings and not isinstance(step_needle.match_settings, HybridFinder):
                matcher = step_needle.match_settings
            else:
                matcher = self.matcher

            matches = matcher.find(step_needle, haystack)
            if len(matches) > 0:
                return matches

        return []
