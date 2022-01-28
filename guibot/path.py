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
Old module for path resolution - to be deprecated.


INTERFACE
------------------------------------------------------

"""

import logging

# Keep the Path class for backward compatibility
# TODO: drop support for this module
from .fileresolver import FileResolver as Path


logging.getLogger("guibot.path")\
    .warn("The `path` module is deprecated, use `fileresolver` instead.")


__all__ = ["Path"]
