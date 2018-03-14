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

import os
from errors import *


import logging
log = logging.getLogger('guibot.path')


class Path(object):
    """
    Handler for currently used target paths or
    sources of targets with a desired name.

    The methods of this class are shared among
    all of its instances.
    """

    # Shared between all instances
    _target_paths = []

    def add_path(self, directory):
        """
        Add a path to the list of currently accessible paths
        if it wasn't already added.

        :param str directory: path to add
        """
        if directory not in Path._target_paths:
            log.info("Adding target path %s", directory)
            Path._target_paths.append(directory)

    def remove_path(self, directory):
        """
        Remove a path from the list of currently accessible paths.

        :param str directory: path to add
        :returns: whether the removal succeeded
        :rtype: bool
        """
        try:
            Path._target_paths.remove(directory)
        except:
            return False

        log.info("Removing target path %s", directory)
        return True

    def clear(self):
        """Clear all currently accessible paths."""
        # empty list but keep reference
        del Path._target_paths[:]

    def search(self, filename, restriction="", silent=False):
        """
        Search for a filename in the currently accessible paths.

        :param str filename: filename of the target to search for
        :param str restriction: simple string to restrict the number of paths
        :param bool silent: whether to return None instead of error out
        :returns: the full name of the found target file or None if silent and no file was found
        :rtype: str or None
        :raises: :py:class:`FileNotFoundError` if no such file was found and not silent
        """
        for directory in Path._target_paths:
            fullname = os.path.join(directory, filename)

            if restriction not in fullname:
                continue
            if os.path.exists(fullname):
                return fullname

            # Check with .png extension for images
            fullname = os.path.join(directory, filename + '.png')
            if os.path.exists(fullname):
                return fullname

            # Check with .xml extension for cascade
            fullname = os.path.join(directory, filename + '.xml')
            if os.path.exists(fullname):
                return fullname

            # Check with .txt extension for text
            fullname = os.path.join(directory, filename + '.txt')
            if os.path.exists(fullname):
                return fullname

            # Check with .pth extension for patterns
            fullname = os.path.join(directory, filename + '.pth')
            if os.path.exists(fullname):
                return fullname

            # Check with .steps extension for chains
            fullname = os.path.join(directory, filename + '.steps')
            if os.path.exists(fullname):
                return fullname

        if not silent:
            raise FileNotFoundError('File ' + filename + ' not found')

        return None
