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


class GuiBenderError(Exception):
    """GuiBender exception base class"""


class FileNotFoundError(GuiBenderError):
    """Exception raised when a picture file cannot be found on disc"""


class FindError(GuiBenderError):
    """Exception raised when an Image cannot be found on the screen"""

    def __init__(self, failed_image=None):
        """
        Build the exception possibly providing the failed image.

        :param failed_image: the image that wasn't found
        :type failed_iamge: :py:class:`image.Image` or None
        """
        if failed_image:
            message = "The image %s could not be found on the screen" % failed_image
        else:
            message = "The image could not be found on the screen"
        super(FindError, self).__init__(message)


class NotFindError(GuiBenderError):
    """Exception raised when an Image can be found on the screen but should not be"""

    def __init__(self, failed_image=None):
        """
        Build the exception possibly providing the failed image.

        :param failed_image: the image that was found
        :type failed_iamge: :py:class:`image.Image` or None
        """
        if failed_image:
            message = "The image %s was found on the screen while it was not expected" % failed_image
        else:
            message = "The image was found on the screen while it was not expected"
        super(NotFindError, self).__init__(message)


class UnsupportedBackendError(GuiBenderError):
    """Exception raised when a non-existent method is used for finding an image"""


class MissingHotmapError(GuiBenderError):
    """Exception raised when an attempt to access a non-existent hotmap in the image logger is made"""


class UninitializedBackendError(GuiBenderError):
    """Exception raised when a region is created within an empty screen (a disconnected desktop control backend)"""
