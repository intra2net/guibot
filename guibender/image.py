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
import copy
import os
import PIL.Image

# TODO: try to use PIL functionality instead
import cv2
import numpy

from settings import Settings
from location import Location
from imagepath import ImagePath
from settings import CVEqualizer


class Image:
    """
    Container for image data supporting caching, clicking target,
    file operations, and preprocessing.
    """

    _cache = {}

    def __init__(self, image_filename=None,
                 pil_image=None, match_settings=None,
                 use_cache=True):
        """
        Build an image object.

        :param image_filename: name of the image file if any
        :type image_filename: str or None
        :param pil_image: image data - use cache or recreate if none
        :type pil_image: :py:class:`PIL.Image` or None
        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`settings.CVEqualizer` or None
        :param bool use_cache: whether to cache image data for better performance
        """
        self._filename = image_filename
        self.match_settings = match_settings
        self._pil_image = pil_image

        if self.match_settings != None:
            self.use_own_settings = True
        else:
            self.use_own_settings = False
        self._width = 0
        self._height = 0
        self._target_center_offset = Location(0, 0)

        if self.filename is not None and (pil_image is None or match_settings is None):
            if not os.path.exists(self.filename):
                self.filename = ImagePath().search(self.filename)

            if pil_image is None:
                # TODO: check if mtime of the file changed -> cache dirty?
                if use_cache and self.filename in self._cache:
                    self._pil_image = self._cache[self.filename]
                else:
                    # load and cache image
                    self._pil_image = PIL.Image.open(self.filename).convert('RGB')
                    if use_cache:
                        self._cache[self.filename] = self._pil_image
            if match_settings is None:
                match_file = self.filename[:-4] + ".match"
                if not os.path.exists(match_file):
                    self.match_settings = CVEqualizer()
                else:
                    self.match_settings = CVEqualizer()
                    self.match_settings.from_match_file(self.filename[:-4])
                    self.use_own_settings = True

        # Set width and height
        if self._pil_image:
            self._width = self._pil_image.size[0]
            self._height = self._pil_image.size[1]

    def __str__(self):
        """Provide the image filename."""
        return os.path.basename(self.filename).replace(".png", "")

    def get_filename(self):
        """
        Getter for readonly attribute.

        :returns: filename of the image
        :rtype: str
        """
        return self._filename
    filename = property(fget=get_filename)

    def get_width(self):
        """
        Getter for readonly attribute.

        :returns: width of the image
        :rtype: int
        """
        return self._width
    width = property(fget=get_width)

    def get_height(self):
        """
        Getter for readonly attribute.

        :returns: height of the image
        :rtype: int
        """
        return self._height
    height = property(fget=get_height)

    def get_pil_image(self):
        """
        Getter for readonly attribute.

        :returns: image data of the image
        :rtype: :py:class:`PIL.Image`
        """
        return self._pil_image
    pil_image = property(fget=get_pil_image)

    def get_similarity(self):
        """
        Getter for readonly attribute.

        :returns: similarity required for the image to be matched
        :rtype: float
        """
        return self.match_settings.p["find"]["similarity"].value
    similarity = property(fget=get_similarity)

    def get_target_center_offset(self):
        """
        Getter for readonly attribute.

        :returns: offset with respect to the image center (used for clicking)
        :rtype: :py:class:`location.Location`
        """
        return self._target_center_offset
    target_center_offset = property(fget=get_target_center_offset)

    def copy(self):
        """
        Perform a copy of the image data and match settings.

        :returns: copy of the current image (with settings)
        :rtype: :py:class:`image.Image`
        """
        copy_settings = copy.deepcopy(self.match_settings)
        selfcopy = copy.copy(self)
        selfcopy.match_settings = copy_settings
        return selfcopy

    def with_target_offset(self, xpos, ypos):
        """
        Perform a copy of the image data without match settings
        and with a newly defined target offset.

        :param int xpos: new offset in the x direction
        :param int ypos: new offset in the y direction
        :returns: copy of the current image with new target offset
        :rtype: :py:class:`image.Image`
        """
        new_image = self.copy()

        new_image.target_center_offset = Location(xpos, ypos)
        return new_image

    def with_similarity(self, new_similarity):
        """
        Perform a copy of the image data without match settings
        and with a newly defined required similarity.

        :param float new_similarity: new required similarity
        :returns: copy of the current image with new similarity
        :rtype: :py:class:`image.Image`
        """
        new_image = self.copy()
        new_image.match_settings.p["find"]["similarity"].value = new_similarity
        return new_image

    def exact(self):
        """
        Perform a copy of the image data without match settings
        and with a maximum required similarity.

        :returns: copy of the current image with maximum similarity
        :rtype: :py:class:`image.Image`
        """
        return self.with_similarity(1.0)

    def save(self, filename):
        """
        Save image to a file.

        :param str filename: name for the image file
        :returns: copy of the current image with the new filename
        :rtype: :py:class:`image.Image`

        The image is compressed upon saving with a PNG compression setting
        specified by :py:func:`settings.Settings.image_quality`.
        """
        self.pil_image.save(filename, compress_level=Settings.image_quality)
        if self.use_own_settings:
            self.match_settings.to_match_file(filename[:-4])

        new_image = self.copy()
        new_image.filename = filename

        return new_image

    def preprocess(self, gray=False):
        """
        Convert the image into a compatible numpy array used for matching.

        :param bool gray: whether to also convert the image into grayscale
        :returns: converted image
        :rtype: :py:class:`numpy.ndarray`

        This format is used by the CV backend.
        """
        searchable_image = numpy.array(self._pil_image)
        # convert RGB to BGR
        searchable_image = searchable_image[:, :, ::-1].copy()
        if gray:
            searchable_image = cv2.cvtColor(searchable_image, cv2.COLOR_BGR2GRAY)
        return searchable_image
