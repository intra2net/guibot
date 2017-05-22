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
from errors import *


class ImagePath(object):
    """
    Handler for currently used image paths or
    sources of images with a desired name.

    The methods of this class are shared among
    all of its instances.
    """

    # Shared between all instances
    _imagePaths = []

    def add_path(self, directory):
        """
        Add a path to the list of currently accessible paths
        if it wasn't already added.

        :param str directory: path to add
        """
        if directory not in ImagePath._imagePaths:
            ImagePath._imagePaths.append(directory)

    def remove_path(self, directory):
        """
        Remove a path from the list of currently accessible paths.

        :param str directory: path to add
        :returns: whether the removal succeeded
        :rtype: bool
        """
        try:
            ImagePath._imagePaths.remove(directory)
        except:
            return False

        return True

    def clear(self):
        """Clear all currently accessible paths."""
        # empty list but keep reference
        del ImagePath._imagePaths[:]

    def search(self, filename):
        """
        Search for a filename in the currently accessible paths.

        :param str filename: filename of the image to search for
        :returns: the full name of the found image file
        :rtype: str
        :raises: :py:class:`FileNotFoundError` if no such file was found
        """
        for directory in ImagePath._imagePaths:
            fullname = os.path.join(directory, filename)
            if os.path.exists(fullname):
                return fullname

            # Check with .png extension
            fullname = os.path.join(directory, filename + '.png')
            if os.path.exists(fullname):
                return fullname

        raise FileNotFoundError('File ' + filename + ' not found')
