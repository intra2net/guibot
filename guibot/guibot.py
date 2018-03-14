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

import logging
log = logging.getLogger('guibot')
log.addHandler(logging.NullHandler())

from path import Path
from region import Region


class GuiBot(Region):
    """
    The main guibot object is the root (first and screen wide) region
    with some convenience functions added.

    .. seealso:: Real API is inherited from :py:class:`region.Region`.
    """

    def __init__(self, dc=None, cv=None):
        """
        Build a guibot object.

        :param dc: DC backend used for any desktop control
        :type dc: :py:class:`desktopcontrol.DesktopControl` or None
        :param cv: CV backend used for any target finding
        :type cv: :py:class:`finder.Finder` or None

        We will initialize with default region of full screen and default
        desktop control and computer vision backends if none are provided.
        """
        super(GuiBot, self).__init__(dc=dc, cv=cv)

        self.path = Path()

    def add_path(self, directory):
        """
        Add a path to the list of currently accessible paths
        if it wasn't already added.

        :param str directory: path to add
        """
        self.path.add_path(directory)

    def remove_path(self, directory):
        """
        Remove a path from the list of currently accessible paths.

        :param str directory: path to add
        """
        self.path.remove_path(directory)
