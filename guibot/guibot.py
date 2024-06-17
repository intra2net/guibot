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
Main guibot interface for GUI automation.

This frontend is recommended for use in most normal cases.


INTERFACE
------------------------------------------------------

"""

import logging

from .fileresolver import FileResolver
from .region import Region
from .controller import Controller
from .finder import Finder


log = logging.getLogger('guibot')
log.addHandler(logging.NullHandler())


class GuiBot(Region):
    """
    The main guibot object is the root (first and screen wide) region
    with some convenience functions added.

    .. seealso:: Real API is inherited from :py:class:`region.Region`.
    """

    def __init__(self, dc: Controller = None, cv: Finder = None) -> None:
        """
        Build a guibot object.

        :param dc: DC backend used for any display control
        :param cv: CV backend used for any target finding

        We will initialize with default region of full screen and default
        display control and computer vision backends if none are provided.
        """
        super(GuiBot, self).__init__(dc=dc, cv=cv)

        self.file_resolver = FileResolver()

    def add_path(self, directory: str) -> None:
        """
        Add a path to the list of currently accessible paths
        if it wasn't already added.

        :param directory: path to add
        """
        self.file_resolver.add_path(directory)

    def remove_path(self, directory: str) -> None:
        """
        Remove a path from the list of currently accessible paths.

        :param directory: path to add
        """
        self.file_resolver.remove_path(directory)
