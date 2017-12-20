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
import shutil

from guibot.config import GlobalConfig
from guibot.path import Path
from guibot.target import Image
from guibot.errors import *
from guibot.finder import *
from guibot.calibrator import Calibrator


# parameters to toy with
NEEDLE = 'n_ibs'
HAYSTACK = 'h_ibs_viewport'
LOGPATH = './tmp/'
REMOVE_LOGPATH = False
CALIBRATED_BENCHMARK = False


# minimal setup
logging.getLogger('').addHandler(logging.StreamHandler())
logging.getLogger('').setLevel(logging.INFO)
GlobalConfig.image_logging_level = 0
GlobalConfig.image_logging_destination = LOGPATH
GlobalConfig.image_logging_step_width = 4

path = Path()
path.add_path('images/')

ImageLogger.step = 1

needle = Image(NEEDLE)
haystack = Image(HAYSTACK)


# the matching step
if GlobalConfig.find_backend == "autopy":
    finder = AutoPyFinder()
elif GlobalConfig.find_backend == "contour":
    finder = ContourFinder()
elif GlobalConfig.find_backend == "template":
    finder = TemplateFinder()
elif GlobalConfig.find_backend == "feature":
    finder = FeatureFinder()
elif GlobalConfig.find_backend == "cascade":
    finder = CascadeFinder()
elif GlobalConfig.find_backend == "text":
    finder = TextFinder()
elif GlobalConfig.find_backend == "tempfeat":
    finder = TemplateFeatureFinder()
elif GlobalConfig.find_backend == "deep":
    finder = DeepFinder()
# non-default initial conditions for the calibration
#finder.configure_backend(find_image = "feature")
#finder.params["find"]["similarity"].value = 0.7
#finder.params["tempfeat"]["front_similarity"].value = 0.5
#finder.params["feature"]["ransacReprojThreshold"].value = 25.0
#finder.params["fdetect"]["nzoom"].value = 7.0
#finder.params["fdetect"]["hzoom"].value = 7.0
#finder.params["fdetect"]["MaxFeatures"].value = 10
finder.find(needle, haystack)


# calibration and benchmarking
calibrator = Calibrator()
error_before = calibrator.calibrate(haystack, needle, finder)
# categories to calibrate
for category in ["find", "feature", "fdetect", "fextract", "fmatch"]:
    finder.can_calibrate(category, True)
error_after = calibrator.calibrate(haystack, needle, finder)
logging.info("Error before and after calibration: %s -> %s", error_before, error_after)
logging.info("Best found parameters:\n%s\n", "\n".join([str(p) for p in finder.params.items()]))
results = calibrator.benchmark(haystack, needle, calibration=CALIBRATED_BENCHMARK)
logging.info("Benchmarking results (method, similarity, location, time):\n%s",
             "\n".join([str(r) for r in results]))


# cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
GlobalConfig.image_logging_level = logging.ERROR
GlobalConfig.image_logging_destination = "./imglog"
GlobalConfig.image_logging_step_width = 3
