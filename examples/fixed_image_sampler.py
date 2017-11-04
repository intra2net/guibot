#!/usr/bin/python

# Only needed if not installed system wide
import sys
sys.path.insert(0, '..')


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

from guibender.settings import GlobalSettings
from guibender.imagelogger import ImageLogger
from guibender.path import Path
from guibender.target import Image
from guibender.errors import *
from guibender.finder import *


# parameters to toy with
NEEDLE = 'shape_blue_circle'
HAYSTACK = 'all_shapes'
LOGPATH = './tmp/'
REMOVE_LOGPATH = False


# minimal setup
logging.getLogger('').addHandler(logging.StreamHandler())
logging.getLogger('').setLevel(logging.DEBUG)
GlobalSettings.image_logging_level = 0
GlobalSettings.image_logging_destination = LOGPATH
GlobalSettings.image_logging_step_width = 4

path = Path()
path.add_path('images/')

ImageLogger.step = 1

needle = Image(NEEDLE)
haystack = Image(HAYSTACK)


# the matching step
if GlobalSettings.find_backend == "autopy":
    finder = AutoPyMatcher()
elif GlobalSettings.find_backend == "contour":
    finder = ContourMatcher()
elif GlobalSettings.find_backend == "template":
    finder = TemplateMatcher()
elif GlobalSettings.find_backend == "feature":
    finder = FeatureMatcher()
elif GlobalSettings.find_backend == "cascade":
    finder = CascadeMatcher()
elif GlobalSettings.find_backend == "text":
    finder = TextMatcher()
elif GlobalSettings.find_backend == "tempfeat":
    finder = TemplateFeatureMatcher()
elif GlobalSettings.find_backend == "deep":
    finder = DeepMatcher()
#finder.configure_backend(find_image = "feature")
#finder.params["find"]["similarity"].value = 0.7
#finder.params["tempfeat"]["front_similarity"].value = 0.5
#finder.params["feature"]["ransacReprojThreshold"].value = 25.0
#finder.params["fdetect"]["nzoom"].value = 7.0
#finder.params["fdetect"]["hzoom"].value = 7.0
#finder.params["fdetect"]["MaxFeatures"].value = 10
finder.find(needle, haystack)


# cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
GlobalSettings.image_logging_level = logging.ERROR
GlobalSettings.image_logging_destination = "./imglog"
GlobalSettings.image_logging_step_width = 3
