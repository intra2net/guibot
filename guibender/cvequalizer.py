# Copyright 2013 Intranet AG / Plamen Dimitrov
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
try:
    import configparser as config
except ImportError:
    import ConfigParser as config

import cv2

from errors import *
from settings import Settings


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
        self.algorithms = {"find_methods" : ("template", "feature", "hybrid"),
                           "template_matchers" : ("autopy", "sqdiff", "ccorr",
                                                  "ccoeff", "sqdiff_normed",
                                                  "ccorr_normed", "ccoeff_normed"),
                           "feature_matchers" : ("BruteForce", "BruteForce-L1",
                                                 "BruteForce-Hamming",
                                                 "BruteForce-Hamming(2)",
                                                 "in-house-raw", "in-house-region"),
                           "feature_detectors" : ("ORB", "FAST", "STAR", "GFTT",
                                                  "HARRIS", "Dense", "oldSURF"),
                           "feature_extractors" : ("ORB", "BRIEF", "FREAK")}

        # parameters registry
        self.p = {"find" : {}, "tmatch" : {}, "fextract" : {}, "fmatch" : {}, "fdetect" : {}}

        # default algorithms
        self._current = {}
        self.configure_backend(find_image = Settings().find_image_backend(),
                               template_match = Settings().template_match_backend(),
                               feature_detect = Settings().feature_detect_backend(),
                               feature_extract = Settings().feature_extract_backend(),
                               feature_match = Settings().feature_match_backend())

    def get_backend(self, category):
        full_names = {"find" : "find_methods",
                      "tmatch" : "template_matchers",
                      "fdetect" : "feature_detectors",
                      "fextract" : "feature_extractors",
                      "fmatch" : "feature_matchers"}
        #print category, self._current[category]
        return self.algorithms[full_names[category]][self._current[category]]

    def set_backend(self, category, value):
        full_names = {"find" : "find_methods",
                      "tmatch" : "template_matchers",
                      "fdetect" : "feature_detectors",
                      "fextract" : "feature_extractors",
                      "fmatch" : "feature_matchers"}
        if value not in self.algorithms[full_names[category]]:
            raise ImageFinderMethodError
        else:
            self._new_params(category, value)
            self._current[category] = self.algorithms[full_names[category]].index(value)

    def configure_backend(self, find_image = None, template_match = None,
                          feature_detect = None, feature_extract = None,
                          feature_match = None):
        """
        Change some or all of the algorithms used as backend for the
        image finder.
        """
        if find_image != None:
            self.set_backend("find", find_image)
        if template_match != None:
            self.set_backend("tmatch", template_match)
        if feature_detect != None:
            self.set_backend("fdetect", feature_detect)
        if feature_extract != None:
            self.set_backend("fextract", feature_extract)
        if feature_match != None:
            self.set_backend("fmatch", feature_match)
 
    def _new_params(self, category, new):
        """Update the parameters dictionary according to a new backend algorithm."""
        self.p[category] = {}
        if category == "find":
            self.p[category]["similarity"] = CVParameter(0.8, 0.0, 1.0, 0.1, 0.1)
            if new in ("feature", "hybrid"):
                self.p[category]["ransacReprojThreshold"] = CVParameter(10.0, 0.0, 200.0, 10.0, 1.0)
            if new in ("template", "hybrid"):
                self.p[category]["nocolor"] = CVParameter(False)
            if new == "hybrid":
                self.p[category]["front_similarity"] = CVParameter(0.4, 0.0, 1.0, 0.1, 0.1)
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
            self.p[category]["nzoom"] = CVParameter(1.0, 1.0, 10.0, 1.0, 1.0)
            self.p[category]["hzoom"] = CVParameter(1.0, 1.0, 10.0, 1.0, 1.0)

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
        #print old_backend, dir(old_backend)
        #print new_backend, dir(new_backend)
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

            # give more information about some better known parameters
            if category in ("fdetect", "fextract") and param == "firstLevel":
                self.p[category][param] = CVParameter(val, 0, 100)
            elif category in ("fdetect", "fextract") and param == "nFeatures":
                self.p[category][param] = CVParameter(val, delta = 100)
            elif category in ("fdetect", "fextract") and param == "WTA_K":
                self.p[category][param] = CVParameter(val, 2, 4)
            elif category in ("fdetect", "fextract") and param == "scaleFactor":
                self.p[category][param] = CVParameter(val, 1.01, 2.0)
            else:
                self.p[category][param] = CVParameter(val)
            #print param, "=", val

        #print category, self.p[category], "\n"
        return

    def sync_backend_to_params(self, opencv_backend, category):
        """
        Synchronize the inner OpenCV parameters of detectors, extractors,
        and matchers with the equalizer.
        """
        if (category == "find" or category == "tmatch" or
            (category == "fdetect" and self.get_backend(category) == "oldSURF")):
            return opencv_backend
        elif category == "fmatch":
            # no internal OpenCV parameters to sync with
            if self.get_backend(category) in ("in-house-raw", "in-house-region"):
                return opencv_backend

            # BUG: a bug of OpenCV leads to crash if parameters
            # are extracted from the matcher interface although
            # the API supports it - skip fmatch for now
            else:
                return opencv_backend

        for param in opencv_backend.getParams():
            if param in self.p[category]:
                val = self.p[category][param].value
                ptype = opencv_backend.paramType(param)
                if ptype == 0:
                    opencv_backend.setInt(param, val)
                elif ptype == 1:
                    opencv_backend.setBool(param, val)
                elif ptype == 2:
                    opencv_backend.setDouble(param, val)
                else:
                    # designed to raise error so that the other ptypes are identified
                    # currently unknown indices: setMat, setAlgorithm, setMatVector, setString
                    #print "synced", param, "to", val
                    val = opencv_backend.setAlgorithm(param, val)
                self.p[category][param].value = val
        return opencv_backend

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
        if(len(success)==0):
            raise IOError

        sections = self.p.keys()
        for section in sections:
            self.set_backend(section, parser.get(section, 'backend'))
            for option in parser.options(section):
                if option == "backend":
                    continue
                param_string = parser.get(section, option)
                param = CVParameter.from_string(param_string)
                #print param_string, param
                self.p[section][option] = param

        #except (config.NoSectionError, config.NoOptionError, ValueError) as ex:
        #    print("Could not read config file '%s': %s." % (filename, ex))
        #    print("Please change or remove the config file.")

    def to_match_file(self, filename_without_extention):
        """Write the equalizer in a .match file with the given filename."""
        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        sections = self.p.keys()
        for section in sections:
            if(not parser.has_section(section)):
                parser.add_section(section)
            parser.set(section, 'backend', self.get_backend(section))
            for option in self.p[section]:
                #print section, option
                parser.set(section, option, self.p[section][option])

        with open("%s.match" % filename_without_extention, 'w') as configfile:
            configfile.write("# IMAGE MATCH DATA\n")
            parser.write(configfile)


class CVParameter:
    """A class for a single parameter from the equalizer."""

    def __init__(self, value,
                 min = None, max = None,
                 delta = 1.0, tolerance = 0.1,
                 fixed = True):
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

        if min != None:
            assert(value >= min)
        if max != None:
            assert(value <= max)
        self.range = (min, max)

        self.fixed = fixed

    def __repr__(self):
        return ("<value='%s' min='%s' max='%s' delta='%s' tolerance='%s' fixed='%s'>"
                % (self.value, self.range[0], self.range[1], self.delta, self.tolerance, self.fixed))

    @staticmethod
    def from_string(repr):
        args = []
        string_args = re.match("<value='(.+)' min='([\d.None]+)' max='([\d.None]+)'"\
                               " delta='([\d.]+)' tolerance='([\d.]+)' fixed='(\w+)'>",
                               repr).group(1, 2, 3, 4, 5, 6)
        for arg in string_args:
            if arg == "None":
                arg = None
            elif arg == "True":
                arg = True
            elif arg == "False":
                arg = False
            elif re.match("\d+$", arg):
                arg = int(arg)
            elif re.match("[\d.]+", arg):
                arg = float(arg)
            else:
                raise ValueError

            #print arg, type(arg)
            args.append(arg)

        #print args
        return CVParameter(*args)
