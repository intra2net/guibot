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
from settings import Settings

# TODO: try to use PIL functionality instead
import cv2
import numpy


class ImageLogger:
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
    logging_level = Settings.image_logging_level
    #: destination for the image logging in order to dump images
    #: (the executing code decides when to clean this directory)
    logging_destination = Settings.image_logging_destination
    #: number of digits for the counter of logged steps
    step_width = Settings.image_logging_step_width

    def __init__(self):
        """Build an imagelogger object."""
        self.needle = None
        self.haystack = None

        self.hotmaps = []
        self.similarities = []
        self.locations = []

        # sync these static methods with the general settings at each use
        ImageLogger.logging_level = Settings.image_logging_level
        # NOTE: the executing code decides when to clean this directory
        ImageLogger.logging_destination = Settings.image_logging_destination
        ImageLogger.step_width = Settings.image_logging_step_width

    def get_printable_step(self):
        """
        Getter for readonly attribute.

        :returns: step number prepended with zeroes to obtain a fixed length enumeration
        :rtype: str
        """
        return ("%0" + str(ImageLogger.step_width) + "d") % ImageLogger.step
    printable_step = property(fget=get_printable_step)

    def debug(self, logtype):
        """
        Log images with a DEBUG logging level.

        :param str logtype: backend algorithm type to log from,
                            see :py:func:`ImageLogger.log` for details
        """
        self.log(10, logtype)

    def info(self, logtype):
        """
        Log images with an INFO logging level.

        :param str logtype: backend algorithm type to log from,
                            see :py:func:`ImageLogger.log` for details
        """
        self.log(20, logtype)

    def warning(self, logtype):
        """
        Log images with a WARNING logging level.

        :param str logtype: backend algorithm type to log from,
                            see :py:func:`ImageLogger.log` for details
        """
        self.log(30, logtype)

    def error(self, logtype):
        """
        Log images with an ERROR logging level.

        :param str logtype: backend algorithm type to log from,
                            see :py:func:`ImageLogger.log` for details
        """
        self.log(40, logtype)

    def critical(self, logtype):
        """
        Log images with a CRITICAL logging level.

        :param str logtype: backend algorithm type to log from,
                            see :py:func:`ImageLogger.log` for details
        """
        self.log(50, logtype)

    def log(self, lvl, logtype):
        """
        Log images with an arbitrary logging level.

        :param int lvl: logging level for the message
        :param str logtype: backend algorithm type to log from,
                            one of 'template', 'autopy', 'feature',
                            'hybrid', and '2to1'
        """
        # below selected logging level
        if lvl < self.logging_level:
            return
        # logging is being collected for a specific logtype
        elif ImageLogger.accumulate_logging:
            return

        if logtype in "template":
            for i in range(len(self.similarities)):
                self.log_locations(30, [self.locations[i]], self.hotmaps[i],
                                   30 * self.similarities[i], 255, 255, 255)
                name = "imglog%s-3hotmap-%s%s-%s.png" % (self.printable_step,
                                                         logtype, i + 1,
                                                         self.similarities[i])
                self.dump_hotmap(name, self.hotmaps[i])

        elif logtype == "autopy":
            self.log_locations(30, self.locations, 30, 0, 0, 0)
            name = "imglog%s-3hotmap-%s.png" % (self.printable_step,
                                                logtype)
            self.dump_hotmap(name, self.hotmaps[-1])

        elif logtype == "feature":
            self.log_locations(30, [self.locations[-1]], self.hotmaps[-1],
                               4, 255, 0, 0)
            name = "imglog%s-3hotmap-%s-%s.png" % (self.printable_step,
                                                   logtype,
                                                   self.similarities[-1])
            self.dump_hotmap(name, self.hotmaps[-1])

        elif logtype == "hybrid":
            # knowing how the hybrid works this estimates
            # the expected number of cases starting from 1 (i+1)
            # to make sure the winner is the first alphabetically
            candidate_num = len(self.similarities) / 2
            for i in range(candidate_num):
                self.log_locations(30, [self.locations[i]],
                                   self.hotmaps[i],
                                   30 * self.similarities[i], 255, 255, 255)
                name = "imglog%s-3hotmap-%s-%stemplate-%s.png" % (self.printable_step,
                                                                  logtype, i + 1,
                                                                  self.similarities[i])
                self.dump_hotmap(name, self.hotmaps[i])
                ii = candidate_num + i
                self.log_locations(30, [self.locations[ii]],
                                   self.hotmaps[ii],
                                   4, 255, 0, 0)
                name = "imglog%s-3hotmap-%s-%sfeature-%s.png" % (self.printable_step,
                                                                 logtype, i + 1,
                                                                 self.similarities[ii])
                self.dump_hotmap(name, self.hotmaps[ii])

            if len(self.similarities) % 2 == 1:
                self.log_locations(30, [self.locations[-1]],
                                   self.hotmaps[-1],
                                   6, 255, 0, 0)
                name = "imglog%s-3hotmap-%s-%s.png" % (self.printable_step,
                                                       logtype,
                                                       self.similarities[-1])
                self.dump_hotmap(name, self.hotmaps[-1])

        elif logtype == "2to1":
            for i in range(len(self.hotmaps)):
                name = "imglog%s-3hotmap-%s-subregion%s-%s.png" % (self.printable_step,
                                                                   logtype, i,
                                                                   self.similarities[i])
                self.dump_hotmap(name, self.hotmaps[i])

        self.clear()
        ImageLogger.step += 1

    def log_locations(self, lvl, locations, hotmap=None,
                      radius=2, r=255, g=255, b=255):
        """
        Draw locations with an arbitrary logging level on a hotmap.

        :param int lvl: logging level for the message
        :param locations: locations on the hotmap that will be circled
        :type locations: [(int, int)]
        :param hotmap: image to draw on where the locations are found
        :type hotmap: :py:class:`numpy.ndarray`
        :param int radius: radius of each circle (preferably integer)
        :param int r: red value of each circle
        :param int g: green value of each circle
        :param int b: blue value of each circle
        """
        if len(self.hotmaps) == 0 and hotmap is None:
            raise MissingHotmapError
        elif hotmap is None:
            hotmap = self.hotmaps[-1]

        if lvl < self.logging_level:
            return
        for loc in locations:
            x, y = loc
            color = (r, g, b)
            cv2.circle(hotmap, (int(x), int(y)), int(radius), color)

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
            self.haystack.filename = "noname.png"
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
        cv2.imwrite(path, hotmap, [cv2.IMWRITE_PNG_COMPRESSION, Settings.image_quality])

    def hotmap_from_template(self, result):
        """
        Produce a hotmap (grayscale image) from an array of similarities.

        :param result: array of similarities obtained from template matching
        :type result: :py:class:`numpy.ndarray`
        :returns: scaled grayscale image that can be visualized or drawn into
        :rtype: :py:class:`numpy.ndarray`
        """
        return result * 255.0

    def clear(self):
        """Clear all accumulated logging including hotmaps, similarities, and locations."""
        self.needle = None
        self.haystack = None
        self.hotmaps = []
        self.similarities = []
        self.locations = []
