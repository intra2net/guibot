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

class Calibrator:
    """
    This class provides with a group of methods to facilitate and
    automate the selection of algorithms and parameters that are most
    successful for a custom image.

    All methods perform benchmarking and calibration of an ImageFinder
    for a given needle Image() and haystack Image().
    """

    def benchmark(self, haystack, needle, imagefinder,
                  calibration = True, tolerance = 0.1,
                  refinements = 50):
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

        @param calibration: whether to use calibration
        @param tolerance: tolerable deviation for all parameters
        @param refinements: number of refinements allowed to improve calibration
        """
        results = []

        # test all template matching methods
        old_config = (imagefinder.eq.current["tmatch"])
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
                imagefinder.eq.current["tmatch"] = key
                start_time = time.time()
                imagefinder.find_template(haystack, needle, 0.0, gray)
                total_time = time.time() - start_time
                #print "%s,%s,%s,%s" % (needle.filename, method, imagefinder.hotmap[1], imagefinder.hotmap[2])
                results.append((method, imagefinder.hotmap[1], imagefinder.hotmap[2], total_time))
        imagefinder.eq.current["tmatch"] = old_config[0]

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
                    imagefinder.eq.current["fdetect"] = key_fd
                    imagefinder.eq.current["fextract"] = key_fe
                    imagefinder.eq.current["fmatch"] = key_fm
                    if calibration:
                        self.calibrate(haystack, needle, imagefinder, tolerance, refinements)
                    start_time = time.time()
                    imagefinder.find_features(haystack, needle, 0.0)
                    total_time = time.time() - start_time
                    method = "%s-%s-%s" % (key_fd, key_fe, key_fm)
                    #print "%s,%s,%s,%s" % (needle.filename, method, imagefinder.hotmap[1], imagefinder.hotmap[2])
                    results.append((method, imagefinder.hotmap[1], imagefinder.hotmap[2], total_time))
        imagefinder.eq.current["fdetect"] = old_config[0]
        imagefinder.eq.current["fextract"] = old_config[1]
        imagefinder.eq.current["fmatch"] = old_config[2]
        return sorted(results, key = lambda x: x[1], reverse = True)

    def calibrate(self, haystack, needle, imagefinder,
                  tolerance = 0.1, refinements = 50):
        """
        Calibrates the available parameters (the equalizer) of an image
        finder for a given needle and haystack.

        Returns the minimized error (in terms of similarity) for the given
        number of refinements and tolerated best parameter range.
        """
        def run(params):
            """
            Internal custom function to evaluate error for a given set of parameters.
            """
            imagefinder.eq.parameters["detect_filter"] = params[0]
            imagefinder.eq.parameters["match_filter"] = params[1]
            imagefinder.eq.parameters["project_filter"] = params[2]

            imagefinder.find_features(haystack, needle, 0.0)
            error = 1.0 - imagefinder.hotmap[1]
            return error


        full_params = []
        full_params.append((0.0, imagefinder.eq.parameters["detect_filter"], 200.0))
        full_params.append((0.0, imagefinder.eq.parameters["match_filter"], 1.0))
        full_params.append((0.0, imagefinder.eq.parameters["project_filter"], 200.0))

        best_params, error = self.twiddle(full_params, run, tolerance, refinements)
        #print best_params, error

        imagefinder.eq.parameters["detect_filter"] = best_params[0]
        imagefinder.eq.parameters["match_filter"] = best_params[1]
        imagefinder.eq.parameters["project_filter"] = best_params[2]

        return error

    def twiddle(self, full_params, run_function, tolerance, max_attempts):
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
        params = [p[1] for p in full_params]
        # the min and max will be checked first with such deltas
        deltas = [(abs(p[2]-p[0])) for p in full_params]

        best_params = params
        best_error = run_function(params)
        #print best_params, best_error

        n = 0
        while sum(deltas) > tolerance and n < max_attempts and best_error > 0.0:
            for i in range(len(params)):
                curr_param = params[i]

                params[i] = min(curr_param + deltas[i], full_params[i][2])
                error = run_function(params)
                if(error < best_error):
                    best_params = params
                    best_error = error
                    deltas[i] *= 1.1
                else:

                    params[i] = max(curr_param - deltas[i], full_params[i][0])
                    error = run_function(params)
                    if(error < best_error):
                        best_params = params
                        best_error = error
                        deltas[i] *= 1.1
                    else:
                        params[i] = curr_param
                        deltas[i] *= 0.9
            #print best_params, best_error
            n += 1

        return (best_params, best_error)
