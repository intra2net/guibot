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

from imagelogger import ImageLogger

import logging
log = logging.getLogger('guibender.calibrator')


class Calibrator:
    """
    Provides with a group of methods to facilitate and automate the selection
    of algorithms and parameters that are most suitable for a given preselected
    image matching pair.

    Use the benchmarking method to choose the best algorithm to find your image.
    Use the calibration method to find the best parameters if you have already
    chosen the algorithm.
    """

    def benchmark(self, haystack, needle, imagefinder,
                  calibration=True, refinements=10):
        """
        Perform benchmarking on all available algorithms of an image finder
        for a given needle and haystack.

        :param haystack: image to look in
        :type haystack: :py:class:`image.Image`
        :param needle: image to look for
        :type needle: :py:class:`image.Image`
        :param imagefinder: CV backend to benchmark
        :type imagefinder: :py:class:`imagefinder.ImageFinder`
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
        """
        results = []
        log.info("Performing benchmarking %s calibration and %s refinements",
                 "with" if calibration else "without", refinements)
        # block logging since we need all its info after the matching finishes
        ImageLogger.accumulate_logging = True

        # test all template matching methods
        old_config = (imagefinder.eq.get_backend("find"),
                      imagefinder.eq.get_backend("tmatch"))
        old_gray = imagefinder.eq.p["find"]["nocolor"].value
        old_similarity = needle.match_settings.p["find"]["similarity"].value
        needle.match_settings.p["find"]["similarity"].value = 0.0
        for key in imagefinder.eq.algorithms["template_matchers"]:
            # autopy does not provide any similarity value
            # and only normed methods are comparable
            if "_normed" not in key:
                continue

            for gray in (True, False):
                if gray:
                    method = key + "_gray"
                else:
                    method = key
                log.debug("Testing %s with %s:", needle.filename, method)

                imagefinder.eq.configure_backend(find_image="template",
                                                 template_match=key)
                imagefinder.eq.p["find"]["nocolor"].value = gray

                start_time = time.time()
                imagefinder.find(needle, haystack)
                total_time = time.time() - start_time
                similarity, location = self._get_last_criteria(imagefinder, total_time)
                results.append((method, similarity, location, total_time))
                imagefinder.imglog.clear()

        imagefinder.eq.configure_backend(find_image=old_config[0],
                                         template_match=old_config[1])
        imagefinder.eq.p["find"]["nocolor"].value = old_gray

        # test all feature matching methods
        old_config = (imagefinder.eq.get_backend("find"),
                      imagefinder.eq.get_backend("fdetect"),
                      imagefinder.eq.get_backend("fextract"),
                      imagefinder.eq.get_backend("fmatch"))
        for key_fd in imagefinder.eq.algorithms["feature_detectors"]:
            # skip in-house because of opencv version bug
            if key_fd == "oldSURF":
                continue

            for key_fe in imagefinder.eq.algorithms["feature_extractors"]:
                for key_fm in imagefinder.eq.algorithms["feature_matchers"]:
                    # Dense feature detection and in-house-region feature matching
                    # are too much performance overhead
                    if key_fd == "Dense" and key_fm == "in-house-region":
                        continue

                    method = "%s-%s-%s" % (key_fd, key_fe, key_fm)
                    log.debug("Testing %s with %s:", needle.filename, method)

                    imagefinder.eq.configure_backend(find_image="feature",
                                                     feature_detect=key_fd,
                                                     feature_extract=key_fe,
                                                     feature_match=key_fm)
                    if calibration:
                        self.calibrate(haystack, needle, imagefinder,
                                       refinements=refinements)

                    start_time = time.time()
                    imagefinder.find(needle, haystack)
                    total_time = time.time() - start_time
                    similarity, location = self._get_last_criteria(imagefinder, total_time)
                    results.append((method, similarity, location, total_time))
                    imagefinder.imglog.clear()

        ImageLogger.accumulate_logging = False
        imagefinder.eq.configure_backend(find_image=old_config[0],
                                         feature_detect=old_config[1],
                                         feature_extract=old_config[2],
                                         feature_match=old_config[3])
        needle.match_settings.p["find"]["similarity"].value = old_similarity
        return sorted(results, key=lambda x: x[1], reverse=True)

    def calibrate(self, haystack, needle, imagefinder,
                  refinements=10, max_exec_time=0.5):
        """
        Calibrate the available parameters (configuration or equalizer) of
        an image finder for a given needle and haystack.

        :param haystack: image to look in
        :type haystack: :py:class:`image.Image`
        :param needle: image to look for
        :type needle: :py:class:`image.Image`
        :param imagefinder: CV backend to calibrate
        :type imagefinder: :py:class:`imagefinder.ImageFinder`
        :param int refinements: maximal number of refinements
        :param float max_exec_time: maximum seconds for a matching attempt
        :returns: minimized error (in terms of similarity)
        :rtype: float

        This method calibrates only parameters that are not protected
        from calibration, i.e. that have `fixed` attribute set to false.
        In order to set all parameters of a background algorithm for calibration
        use the :py:func:`settings.CVEqualizer.can_calibrate` method first.
        """
        def run(params):
            imagefinder.eq.parameters = params

            start_time = time.time()
            try:
                imagefinder.find(needle, haystack)
                similarity = imagefinder.imglog.similarities[-1]
            except:
                log.debug("Time taken is out of the maximum allowable range")
                similarity = 0.0
            total_time = time.time() - start_time
            imagefinder.imglog.clear()

            error = 1.0 - similarity
            error += max(total_time - max_exec_time, 0)
            return error

        # block logging since we need all its info after the matching finishes
        ImageLogger.accumulate_logging = True
        old_similarity = needle.match_settings.p["find"]["similarity"].value
        needle.match_settings.p["find"]["similarity"].value = 0.0
        best_params, error = self.twiddle(imagefinder.eq.p, run, refinements)
        imagefinder.eq.parameters = best_params
        needle.match_settings.p["find"]["similarity"].value = old_similarity
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
                if not params[category][key].fixed:
                    deltas[category][key] = params[category][key].delta

        best_params = params
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
                    if params[category][key].fixed:
                        log.log(0, "fixed: %s %s", category, key)
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
                        best_params = params
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
                            best_params = params
                            best_error = error
                            deltas[category][key] *= 1.1
                        else:
                            param.value = start_value
                            deltas[category][key] *= 0.9

            log.log(0, "%s %s", best_params, best_error)
            n += 1

        return (best_params, best_error)

    def _get_last_criteria(self, imagefinder, total_time):
        assert len(imagefinder.imglog.similarities) == len(imagefinder.imglog.locations)
        if len(imagefinder.imglog.similarities) > 0:
            similarity = imagefinder.imglog.similarities[-1]
            location = imagefinder.imglog.locations[-1]
        else:
            similarity = 0.0
            location = None
        log.debug("%s at %s in %s", similarity, location, total_time)
        return similarity, location
