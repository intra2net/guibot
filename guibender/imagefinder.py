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
import re
import PIL.Image
try:
    import configparser as config
except ImportError:
    import ConfigParser as config

from settings import GlobalSettings, LocalSettings
from location import Location
from imagelogger import ImageLogger
from errors import *

# TODO: OpenCV is required for 95% of the backends so we need to improve the image
# logging and overall image manipulation in order to be able to truly localize its importing
if GlobalSettings.find_image_backend != "autopy":
    import cv2
    import math
    import numpy

import logging
log = logging.getLogger('guibender.imagefinder')


class CVParameter(object):
    """A class for a single parameter from the CV equalizer."""

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
                raise ValueError

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
        self.algorithms["find_methods"] = ("autopy", "template", "feature", "hybrid")

        # other attributes
        self.imglog = ImageLogger()

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

        :param needle: image to look for
        :type needle: :py:class:`image.Image`
        :param haystack: image to look in
        :type haystack: :py:class:`image.Image`
        :param bool multiple: whether to find all matches
        :returns: all found matches (one in most use cases)
        :rtype: [:py:class:`location.Location`]
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Abstract method call - call implementation of this class")


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
        # autopy has diffrent problems on different OS so specify it
        self.params[category]["os_type"] = "linux"

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
        needle.match_settings = self
        needle.use_own_settings = True
        self.imglog.needle = needle
        self.imglog.haystack = haystack
        self.imglog.dump_matched_images()

        if multiple:
            raise NotImplementedError("The backend algorithm AutoPy does not support "
                                      "multiple matches on screen")
        from autopy import bitmap
        from tempfile import NamedTemporaryFile

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
            self.imglog.log(30, "autopy")
            matches = [Location(coord[0], coord[1])]
        else:
            self.imglog.log(30, "autopy")
            matches = []

        return matches


class TemplateMatcher(ImageFinder):
    """Template matching backend provided by OpenCV."""

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using OpenCV's template matching."""
        super(TemplateMatcher, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["template"] = "template_matchers"
        self.algorithms["template_matchers"] = ("sqdiff", "ccorr", "ccoeff","sqdiff_normed",
                                                 "ccorr_normed", "ccoeff_normed")

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
            log.debug('_match_template() returned no result.')
            return []

        universal_hotmap = self.imglog.hotmap_from_template(result)

        # extract maxima once for each needle size region
        similarity = self.params["find"]["similarity"].value
        maxima = []
        while True:

            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
            # switch max and min for sqdiff and sqdiff_normed
            if self.params["template"]["backend"] in ("sqdiff", "sqdiff_normed"):
                # TODO: check whether _template_find_all would work propemultiple for sqdiff
                maxVal = 1 - minVal
                maxLoc = minLoc
            # BUG: Due to an OpenCV bug sqdiff_normed might return a similarity > 1.0
            # although it must be normalized (i.e. between 0 and 1) so patch this and
            # other possible similar bugs
            maxVal = max(maxVal, 0.0)
            maxVal = min(maxVal, 1.0)
            log.debug('Best match with value %s (similarity %s) and location (x,y) %s',
                      str(maxVal), similarity, str(maxLoc))

            if maxVal < similarity:
                if len(maxima) == 0:
                    self.imglog.similarities.append(maxVal)
                    self.imglog.locations.append(maxLoc)
                    self.imglog.hotmaps.append(universal_hotmap)
                log.debug("Best match is not acceptable")
                break
            else:
                log.debug("Best match is acceptable")
                self.imglog.similarities.append(maxVal)
                self.imglog.locations.append(maxLoc)
                self.imglog.hotmaps.append(universal_hotmap)
                maxima.append(Location(maxLoc[0], maxLoc[1]))

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

    def _match_template(self, needle, haystack, nocolor, match):
        """
        EXTRA DOCSTRING: Template matching backend - wrapper.

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
            raise UnsupportedBackendError

        if nocolor:
            gray_needle = needle.preprocess(gray=True)
            gray_haystack = haystack.preprocess(gray=True)
            match = cv2.matchTemplate(gray_haystack, gray_needle, methods[match])
        else:
            opencv_needle = needle.preprocess(gray=False)
            opencv_haystack = haystack.preprocess(gray=False)
            match = cv2.matchTemplate(opencv_haystack, opencv_needle, methods[match])

        return match


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
            self.params[category]["ransacReprojThreshold"] = CVParameter(0.0, 0.0, 200.0, 10.0, 1.0)
        elif category == "fdetect":
            self.params[category]["nzoom"] = CVParameter(4.0, 1.0, 10.0, 1.0, 1.0)
            self.params[category]["hzoom"] = CVParameter(4.0, 1.0, 10.0, 1.0, 1.0)

            if backend == "oldSURF":
                self.params[category]["oldSURFdetect"] = CVParameter(85)
                return
            else:
                feature_detector_create = getattr(cv2, "%s_create" % backend)
                self._detector = backend_obj = feature_detector_create()

        elif category == "fextract":
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

        ngray = needle.preprocess(gray=True)
        hgray = haystack.preprocess(gray=True)
        hcanvas = haystack.preprocess(gray=False)

        # project more points for debugging purposes and image logging
        frame_points = []
        frame_points.append((needle.width / 2, needle.height / 2))
        frame_points.extend([(0, 0), (needle.width, 0), (0, needle.height),
                             (needle.width, needle.height)])

        similarity = self.params["find"]["similarity"].value
        coord = self._project_features(frame_points, ngray, hgray,
                                       similarity, hcanvas)
        matches = [coord] if coord is not None else []

        return matches

    def _project_features(self, locations_in_needle, ngray, hgray,
                          similarity, hotmap_canvas=None):
        """
        EXTRA DOCSTRING: Feature matching backend - wrapper.

        Wrapper for the internal feature detection, matching and location
        projection used by all public feature matching functions.
        """
        # default logging in case no match is found (further overridden by match stages)
        self.imglog.hotmaps.append(hotmap_canvas)
        self.imglog.locations.append((0, 0))
        self.imglog.similarities.append(0.0)

        log.debug("Performing %s feature matching (no color)",
                  "-".join([self.params["fdetect"]["backend"],
                            self.params["fextract"]["backend"],
                            self.params["fmatch"]["backend"]]))
        nkp, ndc, hkp, hdc = self._detect_features(ngray, hgray,
                                                   self.params["fdetect"]["backend"],
                                                   self.params["fextract"]["backend"])

        if len(nkp) < 4 or len(hkp) < 4:
            log.debug("No acceptable best match after feature detection: "
                      "only %s needle and %s haystack features detected",
                      len(nkp), len(hkp))
            self.imglog.log(40, "feature")
            return None

        mnkp, mhkp = self._match_features(nkp, ndc, hkp, hdc,
                                          self.params["fmatch"]["backend"])

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
            location = Location(*self.imglog.locations[-1])
            self.imglog.log(30, "feature")
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
        if nfactor > 1.0:
            log.debug("Zooming x%i needle", nfactor)
            new_shape = (int(ngray.shape[0] * nfactor), int(ngray.shape[1] * nfactor))
            log.log(0, "%s -> %s", ngray.shape, new_shape)
            ngray = cv2.resize(ngray, new_shape)
        if hfactor > 1.0:
            log.debug("Zooming x%i haystack", hfactor)
            new_shape = (int(hgray.shape[0] * hfactor), int(hgray.shape[1] * hfactor))
            log.log(0, "%s -> %s", hgray.shape, new_shape)
            hgray = cv2.resize(hgray, new_shape)

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
            raise UnsupportedBackendError

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
            raise UnsupportedBackendError

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
        self.imglog.log_locations(10, mhkp_locations, None, 2, 0, 255, 255)

        # update the current achieved similarity
        match_similarity = float(len(match_nkeypoints)) / float(len(nkeypoints))
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

        # the match coordinates to be returned
        locations_in_needle.append((0, 0))

        # homography and fundamental matrix as options - homography is considered only
        # for rotation but currently gives better results than the fundamental matrix
        H, mask = cv2.findHomography(numpy.array([kp.pt for kp in mnkp]),
                                     numpy.array([kp.pt for kp in mhkp]), cv2.RANSAC,
                                     self.params["feature"]["ransacReprojThreshold"].value)
        # H, mask = cv2.findFundamentalMat(numpy.array([kp.pt for kp in mnkp]),
        #                                 numpy.array([kp.pt for kp in mhkp]),
        #                                 method = cv2.RANSAC, param1 = 10.0,
        #                                 param2 = 0.9)

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

        self.params["find"]["similarity"].value = template_similarity
        # call specifically the template find variant here
        template_maxima = TemplateMatcher.find(self, needle, haystack, True)

        self.params["find"]["similarity"].value = feature_similarity
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
            up = upleft.y
            down = min(haystack.height, up + needle.height)
            left = upleft.x
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
            return []

        # NOTE: the best of all found will always be logged but if multiple matches
        # are allowed they will all be present on the dumped final canvas
        best_acceptable = max(feature_maxima, key=lambda x: x[1])
        self.imglog.hotmaps.append(hcanvas)
        self.imglog.similarities.append(best_acceptable[1])
        self.imglog.locations.append(best_acceptable[2])
        locations = []
        for maximum in feature_maxima:
            locations.append(Location(*maximum[2]))
        self.imglog.log(30, "hybrid")
        return locations


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
        self.imglog.log(30, "2to1")
        return locations_flat


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
