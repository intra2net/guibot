# Copyright 2013 Intranet AG / Plamen Dimitrov and Thomas Jarosch
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
import logging
from errors import *

class Settings:
    # Shared between all instances
    _drag_delay = 0.5
    _drop_delay = 0.5
    _keys_delay = 0.2
    _rescan_speed_on_find = 0.2
    _save_needle_on_error = True

    def delay_after_drag(self, delay = None):
        if delay == None:
            return Settings._drag_delay
        else:
            Settings._drag_delay = delay

    def delay_before_drop(self, delay = None):
        if delay == None:
            return Settings._drop_delay
        else:
            Settings._drop_delay = delay

    def delay_before_keys(self, delay = None):
        if delay == None:
            return Settings._keys_delay
        else:
            Settings._keys_delay = delay

    def rescan_speed_on_find(self, delay = None):
        if delay == None:
            return Settings._rescan_speed_on_find
        else:
            Settings._rescan_speed_on_find = delay

    def save_needle_on_error(self, value = None):
        if value == None:
            return Settings._save_needle_on_error
        elif value == True or value == False:
            Settings._save_needle_on_error = value
        else:
            raise ValueError
