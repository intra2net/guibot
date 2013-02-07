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

class ImageFinderMethodError(GuiBenderError):
    """Exception raised when a non-existent method is used for finding an image"""
