#!/usr/bin/python

# Only needed if not installed system wide
import sys
sys.path.insert(0, '../..')


# Program start here
#
# Load images/all_shapes.png and images/shape_blue_circle.png
# as a part of haystack and needle, then find the needle in
# the haystack, and dump the results of the matching in a
# tmp folder in examples. The main purpose of this sample is
# to be reused as a tool for matching fixed needle/haystack
# pairs in order to figure out the best parameter configuration
# for successful matching.


import logging
import pprint
import shutil

from guibot.config import GlobalConfig
from guibot.path import Path
from guibot.target import *
from guibot.errors import *
from guibot.finder import *
from guibot.calibrator import Calibrator


# Parameters to toy with
path = Path()
path.add_path('images/')
BACKEND = "template"
# could be Text('Text') or any other target type
NEEDLE = Image('shape_blue_circle')
HAYSTACK = Image('all_shapes')
# calibration/search enabled backend categories
ENABLED = ["template"]  # extra example: ["ocr", "threshold2"]
MAX_ATTEMPTS=10
MAX_EXEC_TIME=1.0
RANDOM_STARTS=10
UNIFORM_DRAW=False
CALIBRATED_SEARCH = False
CALIBRATED_BENCHMARK = False
BENCHMARK_RANDOM_STARTS=0
# image logging variables
LOGPATH = './tmp/'
REMOVE_LOGPATH = False


# Overall logging setup
handler = logging.StreamHandler()
logging.getLogger('').addHandler(handler)
logging.getLogger('').setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
GlobalConfig.image_logging_level = 0
GlobalConfig.image_logging_destination = LOGPATH
GlobalConfig.image_logging_step_width = 4
ImageLogger.step = 1


# Main configuration steps
GlobalConfig.find_backend = BACKEND
if GlobalConfig.find_backend == "autopy":
    finder = AutoPyFinder(synchronize=False)
elif GlobalConfig.find_backend == "contour":
    finder = ContourFinder(synchronize=False)
elif GlobalConfig.find_backend == "template":
    finder = TemplateFinder(synchronize=False)
elif GlobalConfig.find_backend == "feature":
    finder = FeatureFinder(synchronize=False)
elif GlobalConfig.find_backend == "cascade":
    finder = CascadeFinder(synchronize=False)
elif GlobalConfig.find_backend == "text":
    finder = TextFinder(synchronize=False)
elif GlobalConfig.find_backend == "tempfeat":
    finder = TemplateFeatureFinder(synchronize=False)
elif GlobalConfig.find_backend == "deep":
    finder = DeepFinder(synchronize=False)
# non-default initial conditions for the calibration of various finder types
#finder.configure(text_detector="contours")
#finder.configure_backend(backend="sqdiff_normed", category="template")
#finder.params["find"]["similarity"].value = 0.7
#finder.params["tempfeat"]["front_similarity"].value = 0.5
#finder.params["feature"]["ransacReprojThreshold"].value = 25.0
#finder.params["fdetect"]["MaxFeatures"].value = 10
#finder.params["text"]["datapath"].value = "../../misc"
#finder.params["ocr"]["oem"].value = 0
#finder.params["tdetect"]["verticalVariance"].value = 5
#finder.params["threshold"]["blockSize"].value = 3
# synchronize at this stage to take into account all configuration
finder.synchronize()


# Main steps: calibration, searching, and benchmarking
calibrator = Calibrator(NEEDLE, HAYSTACK)
# uncomment this to use a list of needles and haystacks instead
#calibrator = Calibrator(config="pairs.list")
calibrator.run = calibrator.run_performance
# uncomment these for alternative run functions
#calibrator.run = calibrator.run_default
#calibrator.run = calibrator.run_peak
similarity_before = calibrator.calibrate(finder, max_attempts=1)
# categories to calibrate
for category in ENABLED:
    finder.can_calibrate(category, True)
# example parameter to solo allow for calibration:
#finder.params["threshold2"]["blockSize"].fixed = False
similarity_after = calibrator.calibrate(finder, max_attempts=MAX_ATTEMPTS, max_exec_time=MAX_EXEC_TIME)
logging.info("Similarity before and after calibration: %s -> %s", similarity_before, similarity_after)
similarity_global = calibrator.search(finder, random_starts=RANDOM_STARTS, uniform=UNIFORM_DRAW,
                                      calibration=CALIBRATED_SEARCH, max_attempts=MAX_ATTEMPTS, max_exec_time=MAX_EXEC_TIME)
logging.info("Similarity after search (Monte Carlo calibration): %s -> %s", similarity_before, similarity_global)
logging.info("Best found parameters:\n%s", pprint.pformat(finder.params))
results = calibrator.benchmark(finder, random_starts=BENCHMARK_RANDOM_STARTS, uniform=UNIFORM_DRAW,
                               calibration=CALIBRATED_BENCHMARK, max_attempts=MAX_ATTEMPTS, max_exec_time=MAX_EXEC_TIME)
logging.info("Benchmarking results (method, similarity, location, time):\n%s", pprint.pformat(results))


# Final cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
GlobalConfig.image_logging_level = logging.ERROR
GlobalConfig.image_logging_destination = "./imglog"
GlobalConfig.image_logging_step_width = 3
