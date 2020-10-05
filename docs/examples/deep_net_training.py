#!/usr/bin/python3

# Only needed if not installed system wide
import sys
sys.path.insert(0, '../..')


# Program start here
#
# Create a deep network capable of locating a given needle pattern.
# You will need to produce training and testing data as PyTorch tensors
# using the script provided in this project like for instance:
#
#     python misc/generate_pytorch_dataset.py --imglist "train.txt" --isize 150x150 --osize 15x15 --output train.pth
#     python misc/generate_pytorch_dataset.py --imglist "test.txt" --isize 150x150 --osize 15x15 --output test.pth
#
# to produce the data from a list of training or testing image paths and
# location coordinates which could be produced with OpenCV's cascade samples.
# The input and output size parameter have to match those of the configured
# network. This example demonstrated all following steps - network's training,
# testing, configuration, and reuse for a specific matching.

import logging
import shutil

from guibot.config import GlobalConfig
from guibot.imagelogger import ImageLogger
from guibot.fileresolver import FileResolver
from guibot.target import Pattern, Image
from . import CustomFinder
from guibot.errors import *


# Parameters to toy with
file_resolver = FileResolver()
file_resolver.add_path('images/')
NEEDLE = Pattern('shape_blue_circle.pth')
HAYSTACK = Image('all_shapes')
LOGPATH = './tmp/'
REMOVE_LOGPATH = False
EPOCHS_PER_STAGE = 10
TOTAL_STAGES = 10


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


# Main configuration and training steps
finder = CustomFinder()
# use this to load pretrained model and train futher
#import torch
#weights = torch.load(NEEDLE)
#finder.net.load_state_dict(weights)
# use this to configure
#finder.params["find"]["similarity"].value = 0.7
#finder.params["deep"]["use_cuda"].value = False
#finder.params["deep"]["batch_size"].value = 1000
#finder.params["deep"]["log_interval"].value = 10
#finder.params["deep"]["learning_rate"].value = 0.01
#finder.params["deep"]["sgd_momentum"].value = 0.5
#finder.params["deep"]["iwidth"].value = 150
#finder.params["deep"]["iheight"].value = 150
#finder.params["deep"]["owidth"].value = 15
#finder.params["deep"]["oheight"].value = 15
#finder.params["deep"]["channels_conv1"].value = 10
#finder.params["deep"]["kernel_conv1"].value = 5
#finder.params["deep"]["kernel_pool1"].value = 2
#finder.params["deep"]["channels_conv2"].value = 20
#finder.params["deep"]["kernel_conv2"].value = 5
#finder.params["deep"]["kernel_pool2"].value = 2
#finder.params["deep"]["outputs_linear1"].value = 50
for i in range(EPOCHS_PER_STAGE):
    # train for N epochs saving the obtained needle pattern at each stage
    # (which could also be helpful in case the training is interrupted)
    finder.train(TOTAL_STAGES, 'samples_train.pth', 'targets_train.pth', NEEDLE)
    # test trained network on test samples
    finder.test('samples_test.pth', 'targets_test.pth')


# Test trained network on a single test sample with image logging
NEEDLE.use_own_settings = True
settings = NEEDLE.match_settings
matches = finder.find(NEEDLE, HAYSTACK)


# Final cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
GlobalConfig.image_logging_level = logging.ERROR
GlobalConfig.image_logging_destination = "./imglog"
GlobalConfig.image_logging_step_width = 3
