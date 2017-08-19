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
import time
import math
import copy

from imagelogger import ImageLogger

import finder
from errors import *

import logging
log = logging.getLogger('guibender.calibrator')


class Calibrator(object):
    """
    Provides with a group of methods to facilitate and automate the selection
    of algorithms and parameters that are most suitable for a given preselected
    image matching pair.

    Use the benchmarking method to choose the best algorithm to find your image.
    Use the calibration method to find the best parameters if you have already
    chosen the algorithm.
    """

    def benchmark(self, haystack, needle, calibration=True, refinements=10):
        """
        Perform benchmarking on all available algorithms of a finder
        for a given needle and haystack.

        :param haystack: image to look in
        :type haystack: :py:class:`image.Image`
        :param needle: image to look for
        :type needle: :py:class:`image.Image`
        :param bool calibration: whether to use calibration
        :param int refinements: number of refinements allowed to improve calibration
        :returns: list of (method, similarity, location, time) tuples sorted according to similarity
        :rtype: [(str, float, :py:class:`location.Location`, float)]

        This method already uses :py:func:`Calibrator.calibrate` internally
        to provide the best outcome for each compared method (optimal success).
        To turn the calibration off and benchmark with your selected parameters,
        set the `calibration` argument to false.

        .. note:: Methods that are supported by OpenCV but currently don't work are
            excluded from the dictionary. The dictionary can thus also be used to
            assess what are the available and working methods besides their success
            for a given `needle` and `haystack`.
        .. todo:: The calibrator is currently implemented only for the template/feature matchers.
        """
        results = []
        log.info("Performing benchmarking %s calibration and %s refinements",
                 "with" if calibration else "without", refinements)
        # block logging since we need all its info after the matching finishes
        ImageLogger.accumulate_logging = True

        # test all template matching methods
        finder1 = finder.TemplateMatcher()
        needle.match_settings.params["find"]["similarity"].value = 0.0
        for key in finder1.algorithms["template_matchers"]:
            for gray in (True, False):
                if gray:
                    method = key + "_gray"
                else:
                    method = key
                log.debug("Testing %s with %s:", needle.filename, method)

                finder1.configure_backend(key, reset=True)
                finder1.params["template"]["nocolor"].value = gray

                start_time = time.time()
                finder1.find(needle, haystack)
                total_time = time.time() - start_time
                similarity, location = self._get_last_criteria(finder1, total_time)
                results.append((method, similarity, location, total_time))
                finder1.imglog.clear()

        # test all feature matching methods
        finder2 = finder.FeatureMatcher()
        for key_fd in finder2.algorithms["feature_detectors"]:
            for key_fe in finder2.algorithms["feature_extractors"]:
                for key_fm in finder2.algorithms["feature_matchers"]:

                    method = "%s-%s-%s" % (key_fd, key_fe, key_fm)
                    log.debug("Testing %s with %s:", needle.filename, method)

                    finder2.configure(key_fd, key_fe, key_fm)
                    if calibration:
                        self.calibrate(haystack, needle, finder2,
                                       refinements=refinements)

                    start_time = time.time()
                    finder2.find(needle, haystack)
                    total_time = time.time() - start_time
                    similarity, location = self._get_last_criteria(finder2, total_time)
                    results.append((method, similarity, location, total_time))
                    finder2.imglog.clear()

        ImageLogger.accumulate_logging = False
        return sorted(results, key=lambda x: x[1], reverse=True)

    def calibrate(self, haystack, needle, finder,
                  refinements=10, max_exec_time=0.5):
        """
        Calibrate the available parameters (configuration or equalizer) of
        an image finder for a given needle and haystack.

        :param haystack: image to look in
        :type haystack: :py:class:`image.Image`
        :param needle: image to look for
        :type needle: :py:class:`image.Image`
        :param finder: CV backend to calibrate
        :type finder: :py:class:`finder.Finder`
        :param int refinements: maximal number of refinements
        :param float max_exec_time: maximum seconds for a matching attempt
        :returns: minimized error (in terms of similarity)
        :rtype: float

        This method calibrates only parameters that are not protected
        from calibration, i.e. that have `fixed` attribute set to false.
        In order to set all parameters of a background algorithm for calibration
        use the :py:func:`finder.Finder.can_calibrate` method first.

        .. note:: All similarity parameters will be reset to 0.0 after calibration
            and can be set by client code afterwards.
        """
        def run(params):
            finder.params = params

            start_time = time.time()
            try:
                matches = finder.find(needle, haystack)
                # pick similarity of the best match as representative
                similarity = matches[0].similarity
            except:
                log.warn("No match was found at this step (due to internal error or other)")
                similarity = 0.0
            total_time = time.time() - start_time

            # main penalty for bad quality of matching
            error = 1.0 - similarity
            # extra penalty for slow solutions
            error += max(total_time - max_exec_time, 0)
            return error

        # block logging for performance speedup
        ImageLogger.accumulate_logging = True
        # any similarity parameters will be reset to 0.0 to search optimally
        finder.params["find"]["similarity"].value = 0.0
        finder.params["find"]["similarity"].fixed = True
        if "hybrid" in finder.params.keys():
            finder.params["hybrid"]["front_similarity"].value = 0.0
            finder.params["hybrid"]["front_similarity"].fixed = True
        best_params, error = self.twiddle(finder.params, run, refinements)
        finder.params = best_params
        ImageLogger.accumulate_logging = False

        return error

    def twiddle(self, params, run_function, max_attempts):
        """
        Optimize a set of parameters for a minimal matching error.

        :param params: configuration for the CV backend
        :type params: {str, {str, :py:class:`settings.CVParameter`}}
        :param run_function: a function that accepts a list of tested parameters
                             and returns the error that should be minimized
        :type run_function: function
        :param int max_attempts: maximal number of refinements to reach
                                 the parameter delta below the tolerance
        :returns: the configuration with the minimal error
        :rtype: ({str, {str, :py:class:`settings.CVParameter`}}, float)

        .. note:: Special credits for this approach should be given to Prof. Sebastian
            Thrun, who explained it in his Artificial Intelligence for Robotics class.
        """
        deltas = {}
        for category in params.keys():
            deltas[category] = {}
            for key in params[category].keys():
                if (isinstance(params[category][key], finder.CVParameter) and
                        not params[category][key].fixed):
                    deltas[category][key] = params[category][key].delta

        best_params = copy.deepcopy(params)
        best_error = run_function(params)
        log.log(0, "%s %s", best_params, best_error)

        n = 0
        while n < max_attempts and best_error > 0.0:

            # check whether the parameters have all deltas below their tolerance parameters
            all_tolerable = True
            for category in deltas:
                for key in deltas[category]:
                    if deltas[category][key] > params[category][key].tolerance:
                        log.log(0, "%s %s %s", category,
                                key, params[category][key].value)
                        log.log(0, "%s %s", deltas[category][key],
                                params[category][key].tolerance)
                        all_tolerable = False
                        break
            if all_tolerable:
                break

            for category in params.keys():
                for key in params[category].keys():
                    if (isinstance(params[category][key], finder.CVParameter) and
                            params[category][key].fixed):
                        log.log(0, "skip fixed parameter: %s %s", category, key)
                        continue
                    elif key == "backend":
                        continue
                    elif not isinstance(params[category][key], finder.CVParameter):
                        log.warn("The parameter %s-%s is not a CV parameter!", category, key)
                        continue
                    else:
                        param = params[category][key]
                        start_value = param.value

                    # add the delta to the current parameter
                    if type(param.value) == float:
                        if param.range[1] != None:
                            param.value = min(start_value + deltas[category][key],
                                              param.range[1])
                        else:
                            param.value = start_value + deltas[category][key]
                    elif type(param.value) == int:
                        intdelta = int(math.ceil((deltas[category][key])))
                        if param.range[1] != None:
                            param.value = min(start_value + intdelta,
                                              param.range[1])
                        else:
                            param.value = start_value + intdelta
                    elif type(param.value == bool):
                        if param.value:
                            param.value = False
                        else:
                            param.value = True
                    else:
                        continue
                    log.log(0, "+ %s d %s", params, deltas)

                    error = run_function(params)
                    if error < best_error:
                        best_params = copy.deepcopy(params)
                        best_error = error
                        deltas[category][key] *= 1.1
                    else:

                        if type(param.value) == float:
                            if param.range[0] != None:
                                param.value = max(start_value - deltas[category][key],
                                                  param.range[0])
                            else:
                                param.value = start_value - deltas[category][key]
                        elif type(param.value) == int:
                            intdelta = int(math.ceil((deltas[category][key])))
                            if param.range[0] != None:
                                param.value = max(start_value - intdelta,
                                                  param.range[0])
                            else:
                                param.value = start_value - intdelta
                        elif type(param.value) == bool:
                            # the default boolean value was already checked
                            param.value = start_value
                            continue
                        log.log(0, "- %s d %s", params, deltas)

                        error = run_function(params)
                        if error < best_error:
                            best_params = copy.deepcopy(params)
                            best_error = error
                            deltas[category][key] *= 1.1
                        else:
                            param.value = start_value
                            deltas[category][key] *= 0.9

            log.log(0, "%s %s", best_params, best_error)
            n += 1

        return (best_params, best_error)

    def _get_last_criteria(self, finder, total_time):
        if len(finder.imglog.similarities) > 0:
            similarity = finder.imglog.similarities[-1]
            location = finder.imglog.locations[-1]
        else:
            similarity = 0.0
            location = None
        log.debug("%s at %s in %s", similarity, location, total_time)
        return similarity, location
