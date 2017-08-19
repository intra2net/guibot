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


class IncompatibleTargetError(GuiBenderError):
    """Exception raised when a matched target is of type that cannot be handled by the matcher"""


class FindError(GuiBenderError):
    """Exception raised when an Image cannot be found on the screen"""

    def __init__(self, failed_target=None):
        """
        Build the exception possibly providing the failed target.

        :param failed_target: the target that wasn't found
        :type failed_target: :py:class:`target.Target` or None
        """
        if failed_target:
            message = "The target %s could not be found on the screen" % failed_target
        else:
            message = "The target could not be found on the screen"
        super(FindError, self).__init__(message)


class NotFindError(GuiBenderError):
    """Exception raised when an Image can be found on the screen but should not be"""

    def __init__(self, failed_target=None):
        """
        Build the exception possibly providing the failed target.

        :param failed_target: the target that was found
        :type failed_target: :py:class:`target.Target` or None
        """
        if failed_target:
            message = "The target %s was found on the screen while it was not expected" % failed_target
        else:
            message = "The target was found on the screen while it was not expected"
        super(NotFindError, self).__init__(message)


class UnsupportedBackendError(GuiBenderError):
    """Exception raised when a non-existent method is used for finding a target"""


class MissingHotmapError(GuiBenderError):
    """Exception raised when an attempt to access a non-existent hotmap in the image logger is made"""


class UninitializedBackendError(GuiBenderError):
    """Exception raised when a region is created within an empty screen (a disconnected desktop control backend)"""
