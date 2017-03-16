# Copyright 2013 Intranet AG / Thomas Jarosch
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
import os
import shutil

from errors import *
from settings import GlobalSettings

# TODO: try to use PIL functionality instead
import cv2
import numpy


class ImageLogger(object):
    """
    Logger for the image matching process with the help of images.

    It always contains the current match case:
    the needle and haystack images being matched and the hotmap
    (a result image as a numpy array with information about the success),
    the matched similarity and the matched coordinates.

    The image logging consists of saving the last hotmap. If the template
    matching method was used, the hotmap is a fingerprint of the matching
    in the entire haystack. Its lighter areas are places where the needle
    was matched better. If the feature matching method was used, the hotmap
    contains the matched needle features in the haystack (green), the ones
    that were not matched (red), and the points in needle projected to the
    haystack that could be used for clicking, hovering, etc. (blue).
    """

    #: number of the current step
    step = 1
    #: switch to stop logging and later on log all accumulated dumps at once
    accumulate_logging = False

    #: level for the image logging
    logging_level = GlobalSettings.image_logging_level
    #: destination for the image logging in order to dump images
    #: (the executing code decides when to clean this directory)
    logging_destination = GlobalSettings.image_logging_destination
    #: number of digits for the counter of logged steps
    step_width = GlobalSettings.image_logging_step_width

    def __init__(self):
        """Build an imagelogger object."""
        self.needle = None
        self.haystack = None

        self.hotmaps = []
        self.similarities = []
        self.locations = []

        # sync these static methods with the general settings at each use
        ImageLogger.logging_level = GlobalSettings.image_logging_level
        # NOTE: the executing code decides when to clean this directory
        ImageLogger.logging_destination = GlobalSettings.image_logging_destination
        ImageLogger.step_width = GlobalSettings.image_logging_step_width

    def get_printable_step(self):
        """
        Getter for readonly attribute.

        :returns: step number prepended with zeroes to obtain a fixed length enumeration
        :rtype: str
        """
        return ("%0" + str(ImageLogger.step_width) + "d") % ImageLogger.step
    printable_step = property(fget=get_printable_step)

    def debug(self):
        """Log images with a DEBUG logging level."""
        self.log(10)

    def info(self):
        """Log images with an INFO logging level."""
        self.log(20)

    def warning(self):
        """Log images with a WARNING logging level."""
        self.log(30)

    def error(self):
        """Log images with an ERROR logging level."""
        self.log(40)

    def critical(self):
        """Log images with a CRITICAL logging level."""
        self.log(50)

    def log_locations(self, lvl, locations, hotmap,
                      radius=0, r=255, g=255, b=255,
                      draw_needle_box=True):
        """
        Draw locations with an arbitrary logging level on a hotmap.

        :param int lvl: logging level for the message
        :param locations: locations on the hotmap that will be circled
        :type locations: [(int, int)]
        :param hotmap: image to draw on where the locations are found
        :type hotmap: :py:class:`numpy.ndarray`
        :param int radius: radius of each circle (preferably integer)
        :param int b: blue value of each circle
        :param int g: green value of each circle
        :param int r: red value of each circle
        """
        if lvl < self.logging_level:
            return
        for loc in locations:
            x, y = loc
            color = (b, g, r)
            cv2.circle(hotmap, (int(x), int(y)), radius, color)
            if draw_needle_box:
                cv2.rectangle(hotmap, (x, y), (x+self.needle.width, y+self.needle.height), (0, 0, 0), 2)
                cv2.rectangle(hotmap, (x, y), (x+self.needle.width, y+self.needle.height), color, 1)

    def log_window(self, hotmap):
        """
        Show a window with the given hotmap.

        :param hotmap: image (with matching results) to show
        :type hotmap: :py:class:`numpy.ndarray`
        """
        cv2.startWindowThread()
        cv2.namedWindow("hotmap", 1)
        cv2.imshow("hotmap", hotmap)

    def dump_matched_images(self):
        """
        Write file with the current needle and haystack.

        The current needle and haystack (matched images) are stored
        as `needle` and `haystack` attributes.
        """
        if ImageLogger.logging_level > 30:
            return
        if not os.path.exists(ImageLogger.logging_destination):
            os.mkdir(ImageLogger.logging_destination)
        elif ImageLogger.step == 1:
            shutil.rmtree(ImageLogger.logging_destination)
            os.mkdir(ImageLogger.logging_destination)

        if self.needle.filename is None:
            self.needle.filename = "noname"
        needle_name = os.path.basename(self.needle.filename)
        needle_name = "imglog%s-1needle-%s" % (self.printable_step,
                                               needle_name)
        needle_path = os.path.join(ImageLogger.logging_destination,
                                   needle_name)
        self.needle.save(needle_path)

        if self.haystack.filename is None:
            haystack_name = "noname.png"
        else:
            haystack_name = os.path.basename(self.haystack.filename)
        haystack_name = "imglog%s-2haystack-%s" % (self.printable_step,
                                                   haystack_name)
        haystack_path = os.path.join(ImageLogger.logging_destination,
                                     haystack_name)
        self.haystack.save(haystack_path)

    def dump_hotmap(self, name, hotmap):
        """
        Write a file the given hotmap.

        :param str name: filename to use for the image
        :param hotmap: image (with matching results) to write
        :type hotmap: :py:class:`numpy.ndarray`
        """
        if not os.path.exists(ImageLogger.logging_destination):
            os.mkdir(ImageLogger.logging_destination)
        path = os.path.join(ImageLogger.logging_destination, name)
        cv2.imwrite(path, hotmap, [cv2.IMWRITE_PNG_COMPRESSION, GlobalSettings.image_quality])

    def clear(self):
        """Clear all accumulated logging including hotmaps, similarities, and locations."""
        self.needle = None
        self.haystack = None
        self.hotmaps = []
        self.similarities = []
        self.locations = []
