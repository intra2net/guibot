# Copyright 2013-2018 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

"""

SUMMARY
------------------------------------------------------
Image logging for enhanced debugging and verbosity of guibot's operation.


INTERFACE
------------------------------------------------------

"""

import os
import shutil
import PIL.Image
import numpy

from .config import GlobalConfig


class ImageLogger(object):
    """
    Logger for the image matching process with the help of images.

    It always contains the current match case:
    the needle and haystack images/targets being matched and the hotmap
    (an image with additional drawn information on it), the matched
    similarity and the matched coordinates.

    Generally, each finder class takes care of its own image logging,
    performing drawing or similar operations on the spot and deciding
    which hotmaps (also their names and order) to dump.
    """

    #: number of the current step
    step = 1
    #: switch to stop logging and later on log all accumulated dumps at once
    accumulate_logging = False

    #: level for the image logging
    logging_level: int = GlobalConfig.image_logging_level
    #: destination for the image logging in order to dump images
    #: (the executing code decides when to clean this directory)
    logging_destination: str = GlobalConfig.image_logging_destination
    #: number of digits for the counter of logged steps
    step_width: int = GlobalConfig.image_logging_step_width

    def __init__(self) -> None:
        """Build an imagelogger object."""
        self.needle = None
        self.haystack = None

        self.hotmaps = []
        self.similarities = []
        self.locations = []

        # sync these static methods with the general settings at each use
        ImageLogger.logging_level = GlobalConfig.image_logging_level
        # NOTE: the executing code decides when to clean this directory
        ImageLogger.logging_destination = GlobalConfig.image_logging_destination
        ImageLogger.step_width = GlobalConfig.image_logging_step_width

    def get_printable_step(self) -> str:
        """
        Getter for readonly attribute.

        :returns: step number prepended with zeroes to obtain a fixed length enumeration
        """
        return ("%0" + str(ImageLogger.step_width) + "d") % ImageLogger.step

    printable_step = property(fget=get_printable_step)

    def debug(self) -> None:
        """Log images with a DEBUG logging level."""
        self.log(10)

    def info(self) -> None:
        """Log images with an INFO logging level."""
        self.log(20)

    def warning(self) -> None:
        """Log images with a WARNING logging level."""
        self.log(30)

    def error(self) -> None:
        """Log images with an ERROR logging level."""
        self.log(40)

    def critical(self) -> None:
        """Log images with a CRITICAL logging level."""
        self.log(50)

    def dump_matched_images(self) -> None:
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

        needle_name = "imglog%s-1needle-%s" % (self.printable_step, str(self.needle))
        needle_path = os.path.join(ImageLogger.logging_destination, needle_name)
        self.needle.save(needle_path)

        haystack_name = "imglog%s-2haystack-%s" % (
            self.printable_step,
            str(self.haystack),
        )
        haystack_path = os.path.join(ImageLogger.logging_destination, haystack_name)
        self.haystack.save(haystack_path)

    def dump_hotmap(self, name: str, hotmap: PIL.Image.Image | numpy.ndarray) -> None:
        """
        Write a file the given hotmap.

        :param name: filename to use for the image
        :param hotmap: image (with matching results) to write
        """
        if ImageLogger.logging_level > 30:
            return
        if not os.path.exists(ImageLogger.logging_destination):
            os.mkdir(ImageLogger.logging_destination)
        path = os.path.join(ImageLogger.logging_destination, name)

        if isinstance(hotmap, PIL.Image.Image):
            pil_image = hotmap
        else:
            # numpy or other array
            pil_image = PIL.Image.fromarray(hotmap)
            # NOTE: some modes cannot be saved unless converted to RGB
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
        pil_image.save(path, compress_level=GlobalConfig.image_quality)

    def clear(self) -> None:
        """Clear all accumulated logging including hotmaps, similarities, and locations."""
        self.needle = None
        self.haystack = None
        self.hotmaps = []
        self.similarities = []
        self.locations = []
