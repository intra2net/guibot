#!/usr/bin/python
# Only needed if not installed system wide
import sys
sys.path.insert(0, '..')
# end here

#
# Program start here
#
# Load images/all_shapes.png and images/shape_blue_circle.png
# as a pari of hayscack and needle, then find the needle in
# the haystack, and dump the results of the matching in a
# tmp folder in examples. The main purpose of this sample is
# to be reused as a tool for matching fixed needle/haystack
# pairs in order to figure out the best parameter configuration
# for successfull matching.


import os
import re
import unittest
import shutil
import logging

from guibender.settings import Settings
from guibender.imagefinder import ImageFinder
from guibender.imagelogger import ImageLogger
from guibender.imagepath import ImagePath
from guibender.image import Image
from guibender.errors import *

# parameters to toy with
NEEDLE = 'shape_blue_circle'
HAYSTACK = 'all_shapes'
LOGPATH = './tmp/'
REMOVE_LOGPATH = False


Settings.image_logging_level(0)
Settings.image_logging_destination(LOGPATH)
Settings.image_logging_step_width(4)

imagepath = ImagePath()
imagepath.add_path('images/')

ImageLogger.step = 1

needle = Image(NEEDLE)
haystack = Image(HAYSTACK)

needle.use_own_settings = True
settings = needle.match_settings


# MATCHING PARAMETERS START
#settings.configure_backend(find_image = "feature")
#settings.p["find"]["front_similarity"].value = 0.5
#settings.p["find"]["similarity"].value = 0.7
#settings.p["find"]["ransacReprojThreshold"].value = 25.0
#settings.p["fdetect"]["nzoom"].value = 7.0
#settings.p["fdetect"]["hzoom"].value = 7.0
#settings.p["fdetect"]["nFeatures"].value = 1000
# MATCHING PARAMETERS END


# the matching step
finder = ImageFinder()
finder.find(needle, haystack)

# cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
Settings.image_logging_level(logging.ERROR)
Settings.image_logging_destination(".")
Settings.image_logging_step_width(3)
