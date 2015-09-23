# Copyright 2013 Intranet AG / Plamen Dimitrov and Thomas Jarosch
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
import os
try:
    import configparser as config
except ImportError:
    import ConfigParser as config
import logging
log = logging.getLogger('guibender.settings')

import PIL.Image
from tempfile import NamedTemporaryFile

# TODO: make this OpenCV independent with the rest
import cv2

from errors import *


class Settings:
    # operational parameters shared between all instances
    _click_delay = 0.1
    _drag_delay = 0.5
    _drop_delay = 0.5
    _keys_delay = 0.2
    _rescan_speed_on_find = 0.2
    _screen_autoconnect = True
    _preprocess_special_chars = True
    _save_needle_on_error = True
    _image_logging_level = logging.ERROR
    _image_logging_destination = "."
    _image_logging_step_width = 3

    # backends shared between all instances
    _desktop_control_backend = "autopy-nix"
    _find_image_backend = "hybrid"
    _template_match_backend = "ccoeff_normed"
    _feature_detect_backend = "ORB"
    _feature_extract_backend = "BRIEF"
    _feature_match_backend = "BruteForce-Hamming"

    @staticmethod
    def click_delay(delay=None):
        """Timeout before mouse click."""
        if delay == None:
            return Settings._click_delay
        else:
            Settings._click_delay = delay

    @staticmethod
    def delay_after_drag(delay=None):
        """Timeout before drag operation."""
        if delay == None:
            return Settings._drag_delay
        else:
            Settings._drag_delay = delay

    @staticmethod
    def delay_before_drop(delay=None):
        """Timeout before drop operation."""
        if delay == None:
            return Settings._drop_delay
        else:
            Settings._drop_delay = delay

    @staticmethod
    def delay_before_keys(delay=None):
        """Timeout before key press operation."""
        if delay == None:
            return Settings._keys_delay
        else:
            Settings._keys_delay = delay

    @staticmethod
    def rescan_speed_on_find(delay=None):
        """
        Frequency of the image matching attempts (to reduce overhead on the CPU).
        """
        if delay == None:
            return Settings._rescan_speed_on_find
        else:
            Settings._rescan_speed_on_find = delay

    @staticmethod
    def screen_autoconnect(value=None):
        """
        Perform a complete initialization of the desktop control, connecting to
        the backend (screen) selected in the Settings._desktop_control_backend.

        If disabled, you have to connect before performing any GUI operations:
        region.dc_backend.connect_screen()

        The use of this is to allow you to perform some configuration first.
        """
        if value == None:
            return Settings._screen_autoconnect
        elif value == True or value == False:
            Settings._screen_autoconnect = value
        else:
            raise ValueError

    @staticmethod
    def preprocess_special_chars(value=None):
        """
        Preprocess capital and special characters and handle them internally
        (automatic replacement of shift modifier key).

        Warning: The characters will be forcefully preprocessed for the
        autopy-nix (capital and special) and vncdotool (capital) backends.
        """
        if value == None:
            if Settings.desktop_control_backend() == "autopy-nix":
                return True
            elif Settings.desktop_control_backend() == "vncdotool":
                return None
            else:
                return Settings._preprocess_special_chars
        elif value == True or value == False:
            Settings._preprocess_special_chars = value
        else:
            raise ValueError

    @staticmethod
    def save_needle_on_error(value=None):
        """
        Perform an extra dump of the needle on matching error.
        """
        if value == None:
            return Settings._save_needle_on_error
        elif value == True or value == False:
            Settings._save_needle_on_error = value
        else:
            raise ValueError

    @staticmethod
    def image_logging_level(level=None):
        """
        Possible values: similar to the python logging module.

        See the image logging documentation for more details.
        """
        if level == None:
            return Settings._image_logging_level
        else:
            Settings._image_logging_level = level

    @staticmethod
    def image_logging_destination(dest=None):
        """
        String for relative path of the image logging steps.
        """
        if dest == None:
            return Settings._image_logging_destination
        else:
            Settings._image_logging_destination = dest

    @staticmethod
    def image_logging_step_width(width=None):
        """
        Integer to determine the number of digits when enumerating the image
        logging steps, e.g. width=3 for 001, 002, etc.
        """
        if width == None:
            return Settings._image_logging_step_width
        else:
            Settings._image_logging_step_width = width

    @staticmethod
    def desktop_control_backend(name=None):
        """
        Possible backends:
           - autopy-win, autopy-nix - Windows, Linux (and OS X) compatible with
                                      both the GUI actions and their calls
                                      executed on the same machine.
           - qemu - guest OS independent with GUI actions on a virtual machine
                    through Qemu Monitor object (provided by Autotest) and
                    their calls on the host machine.
           - vncdotool - guest OS independent or Linux remote OS with GUI
                         actions on a remote machine through vnc and their
                         calls on a vnc client machine.

        Warning: To use a particular backend you need to satisfy its dependencies,
        i.e. the backend has to be installed or you will have unsatisfied imports.
        """
        if name == None:
            return Settings._desktop_control_backend
        else:
            if name not in ["autopy-win", "autopy-nix", "qemu", "vncdotool"]:
                raise ValueError("Unsupported backend for GUI actions '%s'" % name)
            Settings._desktop_control_backend = name

    # these methods do not check for valid values since this
    # is already done at the equalizer on initialization
    @staticmethod
    def find_image_backend(name=None):
        """
        Possible backends:
            - template - template matching using correlation coefficients,
                         square difference or the default autopy matching.
            - feature - feature matching using a mixture of feature detection,
                        extraction and matching algorithms.
            - hybrid - a mixture of template and feature matching where the
                       first is used as necessary and the second as sufficient stage.

        Warning: To use a particular backend you need to satisfy its dependencies,
        i.e. the backend has to be installed or you will have unsatisfied imports.
        """
        if name == None:
            return Settings._find_image_backend
        else:
            Settings._find_image_backend = name

    @staticmethod
    def template_match_backend(name=None):
        """
        Possible backends: autopy, sqdiff, ccorr, ccoeff, sqdiff_normed,
        ccorr_normed, ccoeff_normed.
        """
        if name == None:
            return Settings._template_match_backend
        else:
            Settings._template_match_backend = name

    @staticmethod
    def feature_detect_backend(name=None):
        """
        Possible backends: BruteForce, BruteForce-L1, BruteForce-Hamming,
        BruteForce-Hamming(2), in-house-raw, in-house-region.
        """
        if name == None:
            return Settings._feature_detect_backend
        else:
            Settings._feature_detect_backend = name

    @staticmethod
    def feature_extract_backend(name=None):
        """
        Possible backends: ORB, FAST, STAR, GFTT, HARRIS, Dense, oldSURF.
        """
        if name == None:
            return Settings._feature_extract_backend
        else:
            Settings._feature_extract_backend = name

    @staticmethod
    def feature_match_backend(name=None):
        """
        Possible backends: ORB, BRIEF, FREAK.
        """
        if name == None:
            return Settings._feature_match_backend
        else:
            Settings._feature_match_backend = name


class DCEqualizer:

    def __init__(self):
        """
        Initialize a class for the desktop control backend configuration.

        This class is similar to the computer vision backend configuration
        one but is simpler due to the lack of categories.

        A parameter can be accessed as follows:
        print self.p["vnc_hostname"]
        """
        self.algorithms = ("autopy-nix", "autopy-win", "qemu", "vncdotool")
        self.p = {}
        self._current = None

        self.configure_backend(Settings.desktop_control_backend())

    def get_backend(self):
        log.log(0, "desktop_control %s", self._current)
        return self._current

    def configure_backend(self, name, *args):
        """
        Change the type and parameters of a backend for the
        desktop control.
        """
        self._current = name
        self._new_params(name)

        if name == "vncdotool":
            if len(args) == 2:
                self.p["vnc_hostname"] = args[0]
                self.p["vnc_port"] = args[1]
            elif len(args) == 1:
                self.p["vnc_port"] = args[0]
        elif name == "qemu":
            if len(args) == 1:
                self.p["qemu_monitor"] = args[0]

    def _new_params(self, new):
        """Update the parameters dictionary according to a new backend method."""
        self.p = {}
        if new == "autopy-nix":
            pass
        elif new == "autopy-wind":
            pass
        elif new == "qemu":
            # qemu monitor object in case qemu backend is used.
            self.p["qemu_monitor"] = None
        elif new == "vncdotool":
            # hostname of the vnc server in case vncdotool backend is used.
            self.p["vnc_hostname"] = "localhost"
            # port of the vnc server in case vncdotool backend is used.
            self.p["vnc_port"] = 0
        log.log(0, "%s %s\n", new, self.p)

    def sync_backend_to_params(self, backend):
        """
        Synchronize the desktop control backend with the equalizer.
        """
        if backend is None:
            backend = DCScreen()
        if self.get_backend() in ["autopy-win", "autopy-nix"]:
            import autopy
            backend.backend = autopy
            # screen size
            screen_size = backend.backend.screen.get_size()
            backend.width = screen_size[0]
            backend.height = screen_size[1]
        elif self.get_backend() == "qemu":
            backend.backend = self.p["qemu_monitor"]
            if backend.backend is None:
                raise ValueError("No Qemu monitor was selected - please set a monitor object first.")
            # screen size
            with NamedTemporaryFile(prefix='guibender', suffix='.ppm') as f:
                filename = f.name
            backend.backend.screendump(filename=filename, debug=True)
            screen = PIL.Image.open(filename)
            os.unlink(filename)
            backend.width = screen.size[0]
            backend.height = screen.size[1]
        elif self.get_backend() == "vncdotool":
            logging.getLogger('vncdotool').setLevel(logging.ERROR)
            logging.getLogger('twisted').setLevel(logging.ERROR)
            from vncdotool import api
            backend.backend = api.connect('%s:%i' % (self.p["vnc_hostname"], self.p["vnc_port"]))
            if Settings.preprocess_special_chars():
                backend.backend.factory.force_caps = True
            # screen size
            with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
                filename = f.name
            screen = backend.backend.captureScreen(filename)
            os.unlink(filename)
            backend.width = screen.width
            backend.height = screen.height
        return backend


class DCScreen:

    """A class for a synchronizable backend with the equalizer."""

    def __init__(self):
        self.backend = None
        self.pointer = (0, 0)
        self.width = 0
        self.height = 0


class CVEqualizer:

    def __init__(self):
        """
        Initiates the CV equalizer with default algorithm configuration.

        Available algorithms:
            template matchers:
                autopy, sqdiff, ccorr, ccoeff
                sqdiff_normed, *ccorr_normed, ccoeff_normed

            feature detectors:
                FAST, STAR, *SIFT, *SURF, ORB, *MSER,
                GFTT, HARRIS, Dense, *SimpleBlob
                *GridFAST, *GridSTAR, ...
                *PyramidFAST, *PyramidSTAR, ...
                *oldSURF (OpenCV 2.2.3)

            feature extractors:
                *SIFT, *SURF, ORB, BRIEF, FREAK

            feature matchers:
                BruteForce, BruteForce-L1, BruteForce-Hamming,
                BruteForce-Hamming(2), **FlannBased,
                in-house-raw, in-house-region

            Starred methods are currently known to be buggy.
            Double starred methods should be investigated further.

        External (image finder) parameters:
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

        Note: "in-house-raw" performs regular knn matching, but "in-house-region"
            performs a special filtering and replacement of matches based on
            positional information (it does not have ratio and symmetry tests
            and assumes that the needle is transformed preserving the relative
            positions of each pair of matches, i.e. no rotation is allowed,
            but scaling for example is supported)
        """
        # currently fully compatible methods
        self.algorithms = {"find_methods": ("template", "feature", "hybrid"),
                           "template_matchers": ("autopy", "sqdiff", "ccorr",
                                                 "ccoeff", "sqdiff_normed",
                                                 "ccorr_normed", "ccoeff_normed"),
                           "feature_matchers": ("BruteForce", "BruteForce-L1",
                                                "BruteForce-Hamming",
                                                "BruteForce-Hamming(2)",
                                                "in-house-raw", "in-house-region"),
                           "feature_detectors": ("ORB", "FAST", "STAR", "GFTT",
                                                 "HARRIS", "Dense", "oldSURF"),
                           "feature_extractors": ("ORB", "BRIEF", "FREAK")}

        # parameters registry
        self.p = {"find": {}, "tmatch": {}, "fextract": {}, "fmatch": {}, "fdetect": {}}

        # default algorithms
        self._current = {}
        self.configure_backend(find_image=Settings.find_image_backend(),
                               template_match=Settings.template_match_backend(),
                               feature_detect=Settings.feature_detect_backend(),
                               feature_extract=Settings.feature_extract_backend(),
                               feature_match=Settings.feature_match_backend())

    def get_backend(self, category):
        full_names = {"find": "find_methods",
                      "tmatch": "template_matchers",
                      "fdetect": "feature_detectors",
                      "fextract": "feature_extractors",
                      "fmatch": "feature_matchers"}
        log.log(0, "%s %s", category, self._current[category])
        return self.algorithms[full_names[category]][self._current[category]]

    def set_backend(self, category, value):
        full_names = {"find": "find_methods",
                      "tmatch": "template_matchers",
                      "fdetect": "feature_detectors",
                      "fextract": "feature_extractors",
                      "fmatch": "feature_matchers"}
        if value not in self.algorithms[full_names[category]]:
            raise ImageFinderMethodError
        else:
            self._new_params(category, value)
            self._current[category] = self.algorithms[full_names[category]].index(value)

    def configure_backend(self, find_image=None, template_match=None,
                          feature_detect=None, feature_extract=None,
                          feature_match=None):
        """
        Change some or all of the algorithms used as backend for the
        image finder.
        """
        if find_image != None:
            log.log(0, "Setting main backend to %s", find_image)
            self.set_backend("find", find_image)
        if template_match != None:
            log.log(0, "Setting backend for template matching to %s", template_match)
            self.set_backend("tmatch", template_match)
        if feature_detect != None:
            log.log(0, "Setting backend for feature detection to %s", feature_detect)
            self.set_backend("fdetect", feature_detect)
        if feature_extract != None:
            log.log(0, "Setting backend for feature extraction to %s", feature_extract)
            self.set_backend("fextract", feature_extract)
        if feature_match != None:
            log.log(0, "Setting backend for feature matching to %s", feature_match)
            self.set_backend("fmatch", feature_match)

    def _new_params(self, category, new):
        """Update the parameters dictionary according to a new backend algorithm."""
        self.p[category] = {}
        if category == "find":
            self.p[category]["similarity"] = CVParameter(0.9, 0.0, 1.0, 0.1, 0.1)
            if new in ("feature", "hybrid"):
                self.p[category]["ransacReprojThreshold"] = CVParameter(0.0, 0.0, 200.0, 10.0, 1.0)
            if new in ("template", "hybrid"):
                self.p[category]["nocolor"] = CVParameter(False)
            if new == "hybrid":
                self.p[category]["front_similarity"] = CVParameter(0.8, 0.0, 1.0, 0.1, 0.1)
            # although it is currently not available
            elif new == "2to1hybrid":
                self.p[category]["x"] = CVParameter(1000, 1, None)
                self.p[category]["y"] = CVParameter(1000, 1, None)
                self.p[category]["dx"] = CVParameter(100, 1, None)
                self.p[category]["dy"] = CVParameter(100, 1, None)
            return
        elif category == "tmatch":
            return
        elif category == "fdetect":
            self.p[category]["nzoom"] = CVParameter(4.0, 1.0, 10.0, 1.0, 1.0)
            self.p[category]["hzoom"] = CVParameter(4.0, 1.0, 10.0, 1.0, 1.0)

            if new == "oldSURF":
                self.p[category]["oldSURFdetect"] = CVParameter(85)
                return
            else:
                new_backend = cv2.FeatureDetector_create(new)

        elif category == "fextract":
            new_backend = cv2.DescriptorExtractor_create(new)
        elif category == "fmatch":
            if new == "in-house-region":
                self.p[category]["refinements"] = CVParameter(50, 1, None)
                self.p[category]["recalc_interval"] = CVParameter(10, 1, None)
                self.p[category]["variants_k"] = CVParameter(100, 1, None)
                self.p[category]["variants_ratio"] = CVParameter(0.33, 0.0001, 1.0)
                return
            else:
                self.p[category]["ratioThreshold"] = CVParameter(0.65, 0.0, 1.0, 0.1)
                self.p[category]["ratioTest"] = CVParameter(False)
                self.p[category]["symmetryTest"] = CVParameter(False)

                # no other parameters are used for the in-house-raw matching
                if new == "in-house-raw":
                    return
                else:

                    # BUG: a bug of OpenCV leads to crash if parameters
                    # are extracted from the matcher interface although
                    # the API supports it - skip fmatch for now
                    return

                    new_backend = cv2.DescriptorMatcher_create(new)

        # examine the interface of the OpenCV backend
        log.log(0, "%s %s", new_backend, dir(new_backend))
        for param in new_backend.getParams():
            log.log(0, "%s", new_backend.paramHelp(param))
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
                log.log(0, "%s %s", param, ptype)
                val = new_backend.getAlgorithm(param)

            # give more information about some better known parameters
            if category in ("fdetect", "fextract") and param == "firstLevel":
                self.p[category][param] = CVParameter(val, 0, 100)
            elif category in ("fdetect", "fextract") and param == "nFeatures":
                self.p[category][param] = CVParameter(val, delta=100)
            elif category in ("fdetect", "fextract") and param == "WTA_K":
                self.p[category][param] = CVParameter(val, 2, 4)
            elif category in ("fdetect", "fextract") and param == "scaleFactor":
                self.p[category][param] = CVParameter(val, 1.01, 2.0)
            else:
                self.p[category][param] = CVParameter(val)
            log.debug("%s=%s", param, val)

        log.log(0, "%s %s\n", category, self.p[category])
        return

    def sync_backend_to_params(self, backend, category):
        """
        Synchronize the desktop control backend with the equalizer.

        In particular, synchronize the inner OpenCV parameters of detectors,
        extractors, and matchers with the equalizer.
        """
        if (category == "find" or category == "tmatch" or
                (category == "fdetect" and self.get_backend(category) == "oldSURF")):
            return backend
        elif category == "fmatch":
            # no internal OpenCV parameters to sync with
            if self.get_backend(category) in ("in-house-raw", "in-house-region"):
                return backend

            # BUG: a bug of OpenCV leads to crash if parameters
            # are extracted from the matcher interface although
            # the API supports it - skip fmatch for now
            else:
                return backend

        for param in backend.getParams():
            if param in self.p[category]:
                val = self.p[category][param].value
                ptype = backend.paramType(param)
                if ptype == 0:
                    backend.setInt(param, val)
                elif ptype == 1:
                    backend.setBool(param, val)
                elif ptype == 2:
                    backend.setDouble(param, val)
                else:
                    # designed to raise error so that the other ptypes are identified
                    # currently unknown indices: setMat, setAlgorithm, setMatVector, setString
                    log.log(0, "Synced %s to %s", param, val)
                    val = backend.setAlgorithm(param, val)
                self.p[category][param].value = val
        return backend

    def can_calibrate(self, mark, category):
        """
        Use this method to fix the parameters for a given
        backend algorithm, i.e. disallow the calibrator to
        change them.

        @param mark: boolean for whether to mark for calibration
        @param category: the backend algorithm category whose parameters
        are marked
        """
        if category not in self.p:
            raise ImageFinderMethodError

        for param in self.p[category].values():
            # BUG: force fix parameters that have internal bugs
            if category == "fextract" and param == "bytes":
                param.fixed = True
            else:
                param.fixed = not mark

    def from_match_file(self, filename_without_extention):
        """Read the equalizer from a .match file with the given filename."""
        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        success = parser.read("%s.match" % filename_without_extention)
        # if no file is found throw an exception
        if len(success) == 0:
            raise IOError

        for category in self.p.keys():
            if parser.has_section(category):
                section_backend = parser.get(category, 'backend')
                if section_backend != self.get_backend(category):
                    self.set_backend(category, section_backend)
                for option in parser.options(category):
                    if option == "backend":
                        continue
                    param_string = parser.get(category, option)
                    param = CVParameter.from_string(param_string)
                    log.log(0, "%s %s", param_string, param)
                    self.p[category][option] = param

        # except (config.NoSectionError, config.NoOptionError, ValueError) as ex:
        #    print("Could not read config file '%s': %s." % (filename, ex))
        #    print("Please change or remove the config file.")

    def to_match_file(self, filename_without_extention):
        """Write the equalizer in a .match file with the given filename."""
        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        sections = self.p.keys()
        for section in sections:
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, 'backend', self.get_backend(section))
            for option in self.p[section]:
                log.log(0, "%s %s", section, option)
                parser.set(section, option, self.p[section][option])

        with open("%s.match" % filename_without_extention, 'w') as configfile:
            configfile.write("# IMAGE MATCH DATA\n")
            parser.write(configfile)


class CVParameter:

    """A class for a single parameter from the equalizer."""

    def __init__(self, value,
                 min_val=None, max_val=None,
                 delta=1.0, tolerance=0.1,
                 fixed=True):
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
        return ("<value='%s' min='%s' max='%s' delta='%s' tolerance='%s' fixed='%s'>"
                % (self.value, self.range[0], self.range[1], self.delta, self.tolerance, self.fixed))

    @staticmethod
    def from_string(raw):
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
