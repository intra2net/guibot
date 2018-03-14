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

import time
import math
import copy

from finder import *
from target import Target
from imagelogger import ImageLogger
from errors import *

import logging
log = logging.getLogger('guibot.calibrator')


class Calibrator(object):
    """
    Provides with a group of methods to facilitate and automate the selection
    of algorithms and parameters that are most suitable for a given preselected
    image matching pair.

    Use the benchmarking method to choose the best algorithm to find your image.
    Use the calibration method to find the best parameters if you have already
    chosen the algorithm. Use the search method to find the best parameters from
    multiple random starts from a uniform or normal probability distribution.
    """

    def __init__(self, needle=None, haystack=None, config=None):
        """
        Build a calibrator object for a given match case.

        :param haystack: image to look in
        :type haystack: :py:class:`target.Image` or None
        :param needle: target to look for
        :type needle: :py:class:`target.Target` or None
        """
        self.cases = []
        if needle is not None and haystack is not None:
            self.cases.append((needle, haystack, True))
        elif config is not None:
            with open(config, "r") as f:
                for line in f.read().splitlines():
                    # each line has the shape "needle.ext haystack.ext max/min"
                    needle, haystack, maximize = line.split(" ")
                    needle = Target.from_data_file(needle)
                    haystack = Target.from_data_file(haystack)
                    maximize = maximize == "max"
                    self.cases.append((needle, haystack, maximize))
                    log.info("Registering match case with needle %s and haystack %s for %s",
                             needle, haystack, "maximizing" if maximize else "minimizing")
        else:
            raise ValueError("Need at least a single needle/haystack for calibration"
                             " or a config file for more than one match case")

        # this attribute can be changed to use different run function
        self.run = self.run_default

    def benchmark(self, finder, random_starts=0, uniform=False,
                  calibration=False, max_attempts=3, **kwargs):
        """
        Perform benchmarking on all available algorithms of a finder
        for a given needle and haystack.

        :param finder: CV backend whose backend algorithms will be benchmarked
        :type finder: :py:class:`finder.Finder`
        :param int random_starts: number of random starts to try with (0 for nonrandom)
        :param bool uniform: whether to use uniform or normal distribution
        :param bool calibration: whether to use calibration
        :param int max_attempts: maximal number of refinements to reach
                                 the parameter delta below the tolerance
        :returns: list of (method, similarity, location, time) tuples sorted according to similarity
        :rtype: [(str, float, :py:class:`location.Location`, float)]

        .. note:: Methods that are supported by OpenCV and others but currently don't work
            are excluded from the dictionary. The dictionary can thus also be used to
            assess what are the available and working methods besides their success
            for a given `needle` and `haystack`.
        """
        results = []
        log.info("Performing benchmarking %s calibration",
                 "with" if calibration else "without")
        # block logging since we need all its info after the matching finishes
        ImageLogger.accumulate_logging = True

        self._prepare_params(finder)
        # obtain all categories in fixed order skipping root categories
        ordered_categories = finder.categories.keys()
        ordered_categories.remove("type")
        ordered_categories.remove("find")

        # test all matching methods of the current finder
        def backend_tuples(category_list, finder):
            if len(category_list) == 0:
                yield ()
            else:
                category = category_list[0]
                backends = finder.algorithms[finder.categories[category]]
                for backend in backends:
                    for z in backend_tuples(category_list[1:], finder):
                        yield (backend,) + z
        for backend_tuple in backend_tuples(ordered_categories, finder):
            method = "+".join(backend_tuple)
            log.info("Benchmark testing with %s", method)

            for backend, category in zip(backend_tuple, ordered_categories):
                finder.configure_backend(backend=backend, category=category, reset=False)
                finder.can_calibrate(category, calibration)

            if random_starts > 0:
                self.search(finder, random_starts=random_starts, uniform=uniform,
                            calibration=calibration, max_attempts=max_attempts, **kwargs)
            elif calibration:
                self.calibrate(finder, max_attempts=max_attempts, **kwargs)

            start_time = time.time()
            similarity = 1.0 - self.run(finder, **kwargs)
            total_time = time.time() - start_time
            log.debug("Obtained similarity %s from %s in %ss", similarity, method, total_time)
            results.append((method, similarity, total_time))

        ImageLogger.accumulate_logging = False
        return sorted(results, key=lambda x: x[1], reverse=True)

    def search(self, finder, random_starts=1, uniform=False,
               calibration=True, max_attempts=3, **kwargs):
        """
        Search for the best match configuration for a given needle and haystack
        using calibration from random initial conditions.

        :param finder: CV backend to use in order to determine deltas, fixed, and free
                       parameters and ultimately tweak to minimize error
        :type finder: :py:class:`finder.Finder`
        :param int random_starts: number of random starts to try with
        :param bool uniform: whether to use uniform or normal distribution
        :param bool calibration: whether to use calibration
        :param int max_attempts: maximal number of refinements to reach
                                 the parameter delta below the tolerance
        :returns: maximized similarity
        :rtype: float

        If normal distribution is used, the mean will be the current value of the
        respective CV parameter and the standard variation will be determined from
        its delta.
        """
        self._prepare_params(finder)
        # block logging for performance speedup
        ImageLogger.accumulate_logging = True
        best_error = self.run(finder, **kwargs)
        best_params = init_params = finder.params
        for i in range(random_starts):
            log.info("Random run %s\%s, best error %s", i+1, random_starts, best_error)

            params = copy.deepcopy(init_params)
            for category in params.keys():
                for key in params[category].keys():
                    param = params[category][key]
                    if not isinstance(param, CVParameter):
                        continue
                    if not param.fixed:
                        mean = None if uniform else param.value
                        deviation = None if uniform else param.delta
                        param.value = param.random_value(mean, deviation)
                        log.debug("Setting %s/%s to random value=%s", category, key, param.value)

            finder.params = params
            if calibration:
                error = 1.0 - self.calibrate(finder, max_attempts=max_attempts, **kwargs)
            else:
                error = self.run(finder, **kwargs)

            if error < best_error:
                log.info("Random start ended with smaller error %s < %s", error, best_error)
                best_error = error
                best_params = params
            else:
                log.debug("Random start did not end with smaller error %s >= %s", error, best_error)

        ImageLogger.accumulate_logging = False
        log.info("Best error for all random starts is %s", best_error)
        finder.params = best_params
        log.log(9, "Best parameters for all random starts:")
        for category in finder.params.keys():
            for key in finder.params[category].keys():
                param = finder.params[category][key]
                if hasattr(param, "value"):
                    log.log(9, "\t%s/%s with value %s +/- delta of %s",
                            category, key, param.value, param.delta)
        return 1.0 - best_error

    def calibrate(self, finder, max_attempts=3, **kwargs):
        """
        Calibrate the available match configuration for a given needle
        and haystack minimizing the matchign error.

        :param finder: configuration for the CV backend to calibrate
        :type finder: :py:class:`finder.Finder`
        :param int max_attempts: maximal number of refinements to reach
                                 the parameter delta below the tolerance
        :returns: maximized similarity
        :rtype: float

        This method calibrates only parameters that are not protected
        from calibration, i.e. that have `fixed` attribute set to false.
        In order to set all parameters of a background algorithm for calibration
        use the :py:func:`finder.Finder.can_calibrate` method first.
        Any parameter values will only be changed if they improve the similarity,
        i.e. minimize the error. The deltas of the final parameters will represent
        the maximal flat regions in positive and/or negative direction where the
        same error is still obtained.

        .. note:: All similarity parameters will be reset to 0.0 after calibration
            and can be set by client code afterwards.

        .. note:: Special credits for this approach should be given to Prof. Sebastian
            Thrun, who explained it in his Artificial Intelligence for Robotics class.
        """
        self._prepare_params(finder)
        # block logging for performance speedup
        ImageLogger.accumulate_logging = True
        best_error = self.run(finder, **kwargs)
        log.log(9, "Calibration start with error=%s", best_error)

        for n in range(max_attempts):
            log.info("Try %s\%s, best error %s", n+1, max_attempts, best_error)

            if best_error == 0.0:
                log.info("Exiting due to zero error")
                break

            slowdown_flag = True
            for category in finder.params.keys():
                for key in finder.params[category].keys():
                    param = finder.params[category][key]
                    if key == "backend":
                        continue
                    elif not isinstance(param, CVParameter):
                        log.warn("The parameter %s/%s is not a CV parameter!", category, key)
                        continue
                    elif param.fixed:
                        log.log(9, "Skip fixed parameter: %s/%s", category, key)
                        continue
                    elif isinstance(param.value, basestring):
                        log.log(9, "Skip string parameter: %s/%s (calibration not supported)", category, key)
                        continue
                    elif param.delta < param.tolerance:
                        log.log(9, "The parameter %s/%s has slowed down to %s below tolerance %s",
                                category, key, param.delta, param.tolerance)
                        continue
                    else:
                        slowdown_flag = False
                        start_value = param.value

                    # add the delta to the current parameter
                    if type(param.value) == float:
                        if param.range[1] != None:
                            param.value = min(start_value + param.delta,
                                              param.range[1])
                        else:
                            param.value = start_value + param.delta
                    elif type(param.value) == int and not param.enumerated:
                        intdelta = int(math.ceil(param.delta))
                        if param.range[1] != None:
                            param.value = min(start_value + intdelta,
                                              param.range[1])
                        else:
                            param.value = start_value + intdelta
                    # remaining types require special handling
                    elif type(param.value) == int and param.enumerated:
                        delta_coeff = 0.9
                        for mode in xrange(*param.range):
                            if start_value == mode:
                                continue
                            param.value = mode
                            error = self.run(finder, **kwargs)
                            log.log(9, "%s/%s: %s +> %s (delta: %s) = %s (best: %s)", category, key,
                                    start_value, param.value, param.delta, error, best_error)
                            if error < best_error:
                                best_error = error
                                param.value = mode
                                delta_coeff = 1.1
                        param.delta *= delta_coeff
                        param.max_delta = param.delta
                        continue
                    elif type(param.value) == bool:
                        if param.value:
                            param.value = False
                        else:
                            param.value = True
                    else:
                        raise ValueError("Parameter %s/%s is of unsupported type %s",
                                         category, key, type(param.value))

                    error = self.run(finder, **kwargs)
                    log.log(9, "%s/%s: %s +> %s (delta: %s) = %s (best: %s)", category, key,
                            start_value, param.value, param.delta, error, best_error)
                    if error < best_error:
                        best_error = error
                        param.delta *= 1.1
                        param.max_delta = param.delta
                    else:

                        if type(param.value) == float:
                            if param.range[0] != None:
                                param.value = max(start_value - param.delta,
                                                  param.range[0])
                            else:
                                param.value = start_value - param.delta
                        elif type(param.value) == int:
                            intdelta = int(math.floor(param.delta))
                            if param.range[0] != None:
                                param.value = max(start_value - intdelta,
                                                  param.range[0])
                            else:
                                param.value = start_value - intdelta
                        elif type(param.value) == bool:
                            # the default boolean value was already checked
                            param.value = start_value
                            continue

                        error = self.run(finder, **kwargs)
                        log.log(9, "%s/%s: %s -> %s (delta: %s) = %s (best: %s)", category, key,
                                start_value, param.value, param.delta, error, best_error)
                        if error < best_error:
                            best_error = error
                            param.delta *= 1.1
                            param.max_delta = param.delta
                        else:

                            param.value = start_value
                            param.delta *= 0.9
                            if error > best_error:
                                param.max_delta = param.delta

            if slowdown_flag:
                log.info("Exiting due to sufficient slowdown for all parameters")
                break

        ImageLogger.accumulate_logging = False
        log.log(9, "Calibration end with error=%s for:", best_error)
        for category in finder.params.keys():
            for key in finder.params[category].keys():
                param = finder.params[category][key]
                if hasattr(param, "value"):
                    if hasattr(param, "max_delta"):
                        param.delta = param.max_delta
                        delattr(param, "max_delta")
                    elif param.fixed:
                        param.delta = 0.0
                    log.log(9, "\t%s/%s with value %s +/- delta of %s",
                            category, key, param.value, param.delta)
        return 1.0 - best_error

    def run_default(self, finder, **_kwargs):
        """
        Run a match case and return error from the match as dissimilarity.

        :param finder: finder with match configuration to use for the run
        :type finder: :py:class:`finder.Finder`
        :returns: error obtained as unity minus similarity
        :rtype: float
        """
        self._handle_restricted_values(finder)

        total_similarity = 0.0
        for needle, haystack, maximize in self.cases:
            try:
                matches = finder.find(needle, haystack)
                # pick similarity of the best match as representative
                similarity = matches[0].similarity
            except:
                log.warn("No match was found at this step (due to internal error or other)")
                similarity = 0.0
            finder.imglog.clear()
            total_similarity += similarity if maximize else 1.0 - similarity

        error = 1.0 - total_similarity / len(self.cases)
        return error

    def run_performance(self, finder, **kwargs):
        """
        Run a match case and return error from the match as dissimilarity
        and linear performance penalty.

        :param finder: finder with match configuration to use for the run
        :type finder: :py:class:`finder.Finder`
        :param float max_exec_time: maximum execution time before penalizing
                                    the run by increasing the error linearly
        :returns: error obtained as unity minus similarity
        :rtype: float
        """
        self._handle_restricted_values(finder)
        max_exec_time = kwargs.get("max_exec_time", 1.0)

        total_similarity = 0.0
        for needle, haystack, maximize in self.cases:
            start_time = time.time()
            try:
                matches = finder.find(needle, haystack)
                # pick similarity of the best match as representative
                similarity = matches[0].similarity
            except:
                log.warn("No match was found at this step (due to internal error or other)")
                similarity = 0.0
            total_time = time.time() - start_time
            finder.imglog.clear()
            total_similarity += similarity if maximize else 1.0 - similarity

        # main penalty for bad quality of matching
        error = 1.0 - total_similarity / len(self.cases)
        # extra penalty for slow solutions (linear)
        error += max(total_time - max_exec_time, 0)
        return error

    def run_peak(self, finder, **kwargs):
        """
        Run a match case and return error from the match as failure to obtain
        high similarity of one match and low similarity of all others.

        :param finder: finder with match configuration to use for the run
        :type finder: :py:class:`finder.Finder`
        :param peak_location: (x, y) of the match whose similarity should be
                              maximized while all the rest minimized
        :type peak_location: (int, int)
        :returns: error obtained as unity minus similarity
        :rtype: float

        This run function doesn't just obtain the optimum similarity for the best
        match in each case of needle and haystack but it minimizes the similarity
        for spatial competitors where spatial means other matches in the same
        haystack. Keep in mind that since matching is performed with zero
        similarity requirement, such matches might not be anything close to the
        needle. This run function finds use cases where the other matches could
        resemble the best one and we want to find configuration to better
        discriminate against those.
        """
        self._handle_restricted_values(finder)
        peak_location = kwargs.get("peak_location", (0,0))

        total_similarity = 0.0
        for needle, haystack, maximize in self.cases:
            subtotal_similarity = 0.0
            try:
                matches = finder.find(needle, haystack)
                for match in matches:
                    if peak_location == (match.x, match.y):
                        subtotal_similarity += match.similarity
                    else:
                        subtotal_similarity += 1.0 - match.similarity
                # final match case similarity is the mean for all matches
                similarity = subtotal_similarity / len(matches)
            except:
                log.warn("No match was found at this step (due to internal error or other)")
                similarity = 0.0
            finder.imglog.clear()
            total_similarity += similarity if maximize else 1.0 - similarity

        error = 1.0 - total_similarity / len(self.cases)
        return error

    def _handle_restricted_values(self, finder):
        if finder.params.has_key("threshold"):
            params = finder.params["threshold"]
            if params["blurKernelSize"].value % 2 == 0:
                params["blurKernelSize"].value += 1
            if params["backend"] == "adaptive" and params["blockSize"].value % 2 == 0:
                params["blockSize"].value += 1
        if finder.params.has_key("threshold2"):
            params = finder.params["threshold2"]
            if params["blurKernelSize"].value % 2 == 0:
                params["blurKernelSize"].value += 1
            if params["backend"] == "adaptive" and params["blockSize"].value % 2 == 0:
                params["blockSize"].value += 1
        if finder.params.has_key("threshold3"):
            params = finder.params["threshold3"]
            if params["blurKernelSize"].value % 2 == 0:
                params["blurKernelSize"].value += 1
            if params["backend"] == "adaptive" and params["blockSize"].value % 2 == 0:
                params["blockSize"].value += 1
        if finder.params.has_key("ocr"):
            params = finder.params["ocr"]
            if params["dt_mask_size"].value not in [0, 3, 5]:
                diffs = {m: abs(m - params["dt_mask_size"].value) for m in [0, 3, 5]}
                params["dt_mask_size"].value = min(diffs, key=diffs.get)

    def _prepare_params(self, finder):
        # any similarity parameters will be reset to 0.0 to search optimally
        finder.params["find"]["similarity"].value = 0.0
        finder.params["find"]["similarity"].fixed = True
        if "tempfeat" in finder.params.keys():
            finder.params["tempfeat"]["front_similarity"].value = 0.0
            finder.params["tempfeat"]["front_similarity"].fixed = True
