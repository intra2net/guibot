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

import os, sys

from imagepath import ImagePath
from region import Region
import logging

# The main guibender object is also a region
# with some convenience functions added

class GuiBender(Region):
    def __init__(self):
        # Init with default region of full screen
        super(GuiBender, self).__init__()

        self.imagepath = ImagePath()

    def add_image_path(self, directory):
        self.imagepath.add_path(directory)

    def remove_image_path(self, directory):
        self.imagepath.remove_path(directory)

    # TODO: Thougts about logging:
    #
    # We should log into an own logger object
    # and chain that into the default logger if wanted.
    #
    # May be the user already uses the python logging module
    # and if we just call logging.info() from everyhere it the code
    # it will pollute the main program log just 'using' guibender (f.e. autotest)
    #
    # May be this will do:
    #     def enable_log(filename_or_parent_logger, log_level, log_on_console=False)
    #     def disable_log()

    # Real API is inherited from Region - see region.py
