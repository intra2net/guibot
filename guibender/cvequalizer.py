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

import cv2

from errors import *


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
        self.parameters = {"find" : {"ransacReprojThreshold" : CVParameter(10.0, 0.0, 200.0, 10.0)},
                           "tmatch" : {}, "fdetect" : {}, "fextract" : {},
                           "fmatch" : {"ratioThreshold" : CVParameter(0.65, 0.0, 1.0, 0.1),
                                       "ratioTest" : CVParameter(False),
                                       "symmetryTest" : CVParameter(False)}}

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
                self.parameters[category]["oldSURFdetect"] = CVParameter(85)
                return
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
                # the API supports it - skip fmatch for now
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

            # give more information about some better known parameters
            if category in ("fdetect", "fextract") and param == "firstLevel":
                self.parameters[category][param] = CVParameter(val, 0, 100)
            elif category in ("fdetect", "fextract") and param == "nFeatures":
                self.parameters[category][param] = CVParameter(val, delta = 100)
            elif category in ("fdetect", "fextract") and param == "WTA_K":
                self.parameters[category][param] = CVParameter(val, 2, 4)
            elif category in ("fdetect", "fextract") and param == "scaleFactor":
                self.parameters[category][param] = CVParameter(val, 1.01, 2.0)
            elif category == "fextract" and param == "bytes":
                self.parameters[category][param] = CVParameter(val, fixed = True)
            else:
                self.parameters[category][param] = CVParameter(val)
            #print param, "=", val

        #print category, self.parameters[category], "\n"
        return

    def sync_backend_to_params(self, opencv_backend, category):
        """
        Synchronize the inner OpenCV parameters of detectors, extractors,
        and matchers with the equalizer.
        """
        if (category == "find" or category == "tmatch" or
            (category == "fdetect" and self.current[category] == "oldSURF")):
            return opencv_backend
        elif category == "fmatch":
            if self.current[category] == "in-house":
                return opencv_backend

            # BUG: a bug of OpenCV leads to crash if parameters
            # are extracted from the matcher interface although
            # the API supports it - skip fmatch for now
            return opencv_backend

        for param in opencv_backend.getParams():
            if param in self.parameters[category]:
                val = self.parameters[category][param].value
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
                self.parameters[category][param].value = val
        return opencv_backend


class CVParameter:
    """A class for a single parameter from the equalizer."""

    def __init__(self, value, min = None, max = None,
                 delta = 1.0, fixed = False):
        self.value = value

        if min != None:
            assert(value >= min)
        if max != None:
            assert(value <= max)
        self.range = (min, max)

        self.fixed = fixed

    def __repr__(self):
        return "<CVParam %s>" % self.value
