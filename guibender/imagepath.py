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


class ImagePath:
    # Shared between all instances
    _imagePaths = []

    def add_path(self, directory):
        if directory not in ImagePath._imagePaths:
            ImagePath._imagePaths.append(directory)

    def remove_path(self, directory):
        try:
            ImagePath._imagePaths.remove(directory)
        except:
            return False

        return True

    def clear(self):
        # empty list but keep reference
        del ImagePath._imagePaths[:]

    def search(self, filename):
        for directory in ImagePath._imagePaths:
            fullname = os.path.join(directory, filename)
            if os.path.exists(fullname):
                return fullname

            # Check with .png extension
            fullname = os.path.join(directory, filename + '.png')
            if os.path.exists(fullname):
                return fullname

        raise FileNotFoundError('File ' + filename + ' not found')
