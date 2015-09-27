#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch and Plamen Dimitrov
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

import logging
log = logging.getLogger('guibender')
log.addHandler(logging.NullHandler())

from imagepath import ImagePath
from region import Region


class GuiBender(Region):

    """
    The main guibender object is also a region
    with some convenience functions added.
    """

    def __init__(self, dc=None, cv=None):
        # initialize with default region of full screen and own
        # desktop control and computer vision backends
        super(GuiBender, self).__init__(dc=dc, cv=cv)

        self.imagepath = ImagePath()

    def add_image_path(self, directory):
        log.info("Adding image path %s", directory)
        self.imagepath.add_path(directory)

    def remove_image_path(self, directory):
        log.info("Removing image path %s", directory)
        self.imagepath.remove_path(directory)

    # Real API is inherited from Region - see region.py
