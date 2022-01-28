# Copyright 2013-2020 Intranet AG and contributors
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
Cached and reused paths for target files to search in and load target data from.


INTERFACE
------------------------------------------------------

"""

import os
from .errors import *

import logging


log = logging.getLogger('guibot.path')


class FileResolver(object):
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
        if directory not in FileResolver._target_paths:
            log.info("Adding target path %s", directory)
            FileResolver._target_paths.append(directory)

    def remove_path(self, directory):
        """
        Remove a path from the list of currently accessible paths.

        :param str directory: path to add
        :returns: whether the removal succeeded
        :rtype: bool
        """
        try:
            FileResolver._target_paths.remove(directory)
        except ValueError:
            return False

        log.info("Removing target path %s", directory)
        return True

    def clear(self):
        """Clear all currently accessible paths."""
        # empty list but keep reference
        del FileResolver._target_paths[:]

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
        for directory in FileResolver._target_paths:
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

            # Check with .csv extension for patterns
            fullname = os.path.join(directory, filename + '.csv')
            if os.path.exists(fullname):
                return fullname

            # Check with .steps extension for chains
            fullname = os.path.join(directory, filename + '.steps')
            if os.path.exists(fullname):
                return fullname

        if not silent:
            raise FileNotFoundError('File ' + filename + ' not found')

        return None

    def __iter__(self):
        for p in self._target_paths:
            yield p

    def __len__(self):
        return len(self._target_paths)


class CustomFileResolver(object):
    """
    Class to be used to search for files inside certain paths.

    Inside the context of an instance of this class, the paths
    in the shared list in :py:class:`FileResolver` will be temporarily
    replaced by the paths passed to the constructor of this class.
    This means that any call to :py:func:`FileResolver.search` will
    take only these paths into account.
    """

    def __init__(self, *paths):
        """
        Create the class with the paths that the search will be
        restricted to.

        :param paths: list of paths that the search will use
        """
        self._paths = paths

    def __enter__(self):
        """
        Start this context.

        :returns: instance of the file resolver that can be used to search files
        :rtype: py:class:`FileResolver`

        The paths used by the py:class:`FileResolver` class will be replaced by
        the paths used to initialize this class during the duration of this context.
        """
        file_resolver = FileResolver()
        self._old_paths = list(file_resolver)
        file_resolver.clear()
        for p in self._paths:
            file_resolver.add_path(p)
        return file_resolver

    def __exit__(self, *args):
        """
        Exit this context and restore the original paths.

        :param args: default args passed when exiting context
        """
        file_resolver = FileResolver()
        for p in self._old_paths:
            file_resolver.add_path(p)
