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
    This class is reponsible for logging the image matching process
    with the help of images. It always contains the current match
    case: the needle and haystack images being matched and the hotmap -
    a result image as a numpy array with information about the success,
    the matched similarity and the matched coordinates.
    """

    step = 1
    accumulate_logging = False

    logging_level = Settings.image_logging_level()
    # NOTE: the executing code decides when to clean this directory
    logging_destination = Settings.image_logging_destination()
    step_width = Settings.image_logging_step_width()

    def get_printable_step(self):
        return ("%0" + str(ImageLogger.step_width) + "d") % ImageLogger.step
    printable_step = property(fget=get_printable_step)

    def __init__(self):
        self.needle = None
        self.haystack = None

        self.hotmaps = []
        self.similarities = []
        self.locations = []

        # sync these static methods with the general settings at each use
        ImageLogger.logging_level = Settings.image_logging_level()
        # NOTE: the executing code decides when to clean this directory
        ImageLogger.logging_destination = Settings.image_logging_destination()
        ImageLogger.step_width = Settings.image_logging_step_width()

    def debug(self, logtype):
        self.log(10, logtype)

    def info(self, logtype):
        self.log(20, logtype)

    def warning(self, logtype):
        self.log(30, logtype)

    def error(self, logtype):
        self.log(40, logtype)

    def critical(self, logtype):
        self.log(50, logtype)

    def log(self, lvl, logtype):
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
        cv2.startWindowThread()
        cv2.namedWindow("hotmap", 1)
        cv2.imshow("hotmap", hotmap)

    def dump_matched_images(self):
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
        if not os.path.exists(ImageLogger.logging_destination):
            os.mkdir(ImageLogger.logging_destination)
        path = os.path.join(ImageLogger.logging_destination, name)
        cv2.imwrite(path, hotmap, [cv2.IMWRITE_PNG_COMPRESSION, Settings.image_quality()])

    def hotmap_from_template(self, result):
        return result * 255.0

    def clear(self):
        self.needle = None
        self.haystack = None
        self.hotmaps = []
        self.similarities = []
        self.locations = []
