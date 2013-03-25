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
import time, math

class Calibrator:
    """
    This class provides with a group of methods to facilitate and
    automate the selection of algorithms and parameters that are most
    successful for a custom image.

    All methods perform benchmarking and calibration of an ImageFinder
    for a given needle Image() and haystack Image().
    """

    def benchmark(self, haystack, needle, imagefinder,
                  calibration = True, refinements = 10):
        """
        Performs benchmarking on all available algorithms and returns a list of
        (method, success, coordinates, time) tuples sorted according to
        similarity (success).

        Use this method to choose the best algorithm to find your specific image
        (or image category). Use the "calibrate" method to find the best parameters
        if you have already chosen the algorithm.

        Note: This method already uses calibrate internally to provide the best
        outcome for each compared method (optimal success). You will not gain
        the same result if you don't calibrate the parameters. To turn the calibration
        off and benchmark with your selected parameters, change the "calibration"
        function argument.

        Note: Methods that are supported by OpenCV but currently don't work are
        excluded from the dictionary. The dictionary can thus also be used
        to assess what are the available and working methods besides their success
        for a given needle and haystack.

        @param imagefinder: the ImageFinder instance to use for the benchmarking
        @param calibration: whether to use calibration
        @param refinements: number of refinements allowed to improve calibration
        """
        results = []

        # test all template matching methods
        old_config = (imagefinder.eq.current["tmatch"])
        old_similarity = needle.match_settings.parameters["find"]["similarity"].value
        needle.match_settings.parameters["find"]["similarity"].value = 0.0
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
                imagefinder.eq.configure_backend(template_match = key)
                start_time = time.time()
                imagefinder.template_find(haystack, needle, gray)
                total_time = time.time() - start_time
                #print "%s,%s,%s,%s" % (needle.filename, method, imagefinder.hotmap[1], imagefinder.hotmap[2])
                results.append((method, imagefinder.hotmap[1], imagefinder.hotmap[2], total_time))
        imagefinder.eq.configure_backend(template_match = old_config)

        # test all feature matching methods
        old_config = (imagefinder.eq.current["fdetect"],
                      imagefinder.eq.current["fextract"],
                      imagefinder.eq.current["fmatch"])
        for key_fd in imagefinder.eq.algorithms["feature_detectors"]:
            # skip in-house because of opencv version bug
            if key_fd == "oldSURF":
                continue
            for key_fe in imagefinder.eq.algorithms["feature_extractors"]:
                for key_fm in imagefinder.eq.algorithms["feature_matchers"]:
                    imagefinder.eq.configure_backend(feature_detect = key_fd,
                                                     feature_extract = key_fe,
                                                     feature_match = key_fm)
                    if calibration:
                        self.calibrate(haystack, needle, imagefinder,
                                       refinements = refinements)
                    start_time = time.time()
                    imagefinder.feature_find(haystack, needle)
                    total_time = time.time() - start_time
                    method = "%s-%s-%s" % (key_fd, key_fe, key_fm)
                    #print "%s,%s,%s,%s" % (needle.filename, method, imagefinder.hotmap[1], imagefinder.hotmap[2])
                    results.append((method, imagefinder.hotmap[1],
                                    imagefinder.hotmap[2], total_time))

        imagefinder.eq.configure_backend(feature_detect = old_config[0],
                                         feature_extract = old_config[1],
                                         feature_match = old_config[2])
        needle.match_settings.parameters["find"]["similarity"].value = old_similarity
        return sorted(results, key = lambda x: x[1], reverse = True)

    def calibrate(self, haystack, needle, imagefinder,
                  refinements = 10, max_exec_time = 0.5):
        """
        Calibrates the available parameters (the equalizer) of an image
        finder for a given needle and haystack.

        Returns the minimized error (in terms of similarity) for the given
        maximal execution time (in seconds) and number of refinements.

        Note: This method calibrates only parameters that are not protected
        from calibration, i.e. that have "fixed" attribute set to False.
        In order to set all parameters of a background algorithm for calibration
        use the "can_calibrate" method of the equalizer first.
        """
        def run(params):
            """
            Internal custom function to evaluate error for a given set of parameters.
            """
            imagefinder.eq.parameters = params

            start_time = time.time()
            try:
                imagefinder.feature_find(haystack, needle)
            except:
                #print "out of range"
                imagefinder.hotmap[1] = 0.0
            total_time = time.time() - start_time

            error = 1.0 - imagefinder.hotmap[1]
            error += max(total_time - max_exec_time, 0)
            return error

        old_similarity = needle.match_settings.parameters["find"]["similarity"].value
        needle.match_settings.parameters["find"]["similarity"].value = 0.0
        best_params, error = self.twiddle(imagefinder.eq.parameters,
                                          run, refinements)
        imagefinder.eq.parameters = best_params
        needle.match_settings.parameters["find"]["similarity"].value = old_similarity

        return error

    def twiddle(self, params, run_function, max_attempts):
        """
        Function to optimize a set of parameters for a minimal returned error.

        @param parameters: a list of parameter triples of the form (min, start, max)
        @param run_function: a function that accepts a list of tested parameters
        and returns the error that should be minimized
        @param tolerance: minimal parameter delta (uncertainty interval)
        @param max_attempts: maximal number of refinements to reach the parameter
        delta below the tolerance.

        Special credits for this approach should be given to Prof. Sebastian Thrun,
        who explained it in his Artificial Intelligence for Robotics class.
        """
        deltas = {}
        for category in params.keys():
            deltas[category] = {}
            for key in params[category].keys():
                if not params[category][key].fixed:
                    deltas[category][key] = params[category][key].delta

        best_params = params
        best_error = run_function(params)
        #print best_params, best_error

        n = 0
        while n < max_attempts and best_error > 0.0:

            # check whether the parameters have all deltas below their tolerance parameters
            all_tolerable = True
            for category in deltas:
                for key in deltas[category]:
                    if deltas[category][key] > params[category][key].tolerance:
                        #print category, key, params[category][key].value
                        #print deltas[category][key], params[category][key].tolerance
                        all_tolerable = False
                        break
            if all_tolerable:
                break

            for category in params.keys():
                for key in params[category].keys():
                    if params[category][key].fixed:
                        #print "fixed:", category, key
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
                    #print "+", params, deltas

                    error = run_function(params)
                    if(error < best_error):
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
                        #print "-", params, deltas

                        error = run_function(params)
                        if(error < best_error):
                            best_params = params
                            best_error = error
                            deltas[category][key] *= 1.1
                        else:
                            param.value = start_value
                            deltas[category][key] *= 0.9

            #print best_params, best_error
            n += 1

        return (best_params, best_error)
