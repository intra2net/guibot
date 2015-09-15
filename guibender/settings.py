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
import logging


class Settings:
    # operational parameters shared between all instances
    _os_name = "Linux"
    _drag_delay = 0.5
    _drop_delay = 0.5
    _keys_delay = 0.2
    _rescan_speed_on_find = 0.2
    _save_needle_on_error = True
    _image_logging_level = logging.ERROR
    _image_logging_destination = "."
    _image_logging_step_width = 3

    # backends shared between all instances
    _desktop_control_backend = "autopy"
    _find_image_backend = "hybrid"
    _template_match_backend = "ccoeff_normed"
    _feature_detect_backend = "ORB"
    _feature_extract_backend = "BRIEF"
    _feature_match_backend = "BruteForce-Hamming"

    @staticmethod
    def os_name(name=None):
        if name == None:
            return Settings._os_name
        else:
            Settings._os_name = name

    @staticmethod
    def delay_after_drag(delay=None):
        if delay == None:
            return Settings._drag_delay
        else:
            Settings._drag_delay = delay

    @staticmethod
    def delay_before_drop(delay=None):
        if delay == None:
            return Settings._drop_delay
        else:
            Settings._drop_delay = delay

    @staticmethod
    def delay_before_keys(delay=None):
        if delay == None:
            return Settings._keys_delay
        else:
            Settings._keys_delay = delay

    @staticmethod
    def rescan_speed_on_find(delay=None):
        if delay == None:
            return Settings._rescan_speed_on_find
        else:
            Settings._rescan_speed_on_find = delay

    @staticmethod
    def save_needle_on_error(value=None):
        if value == None:
            return Settings._save_needle_on_error
        elif value == True or value == False:
            Settings._save_needle_on_error = value
        else:
            raise ValueError

    @staticmethod
    def image_logging_level(level=None):
        if level == None:
            return Settings._image_logging_level
        else:
            Settings._image_logging_level = level

    @staticmethod
    def image_logging_destination(dest=None):
        if dest == None:
            return Settings._image_logging_destination
        else:
            Settings._image_logging_destination = dest

    @staticmethod
    def image_logging_step_width(width=None):
        if width == None:
            return Settings._image_logging_step_width
        else:
            Settings._image_logging_step_width = width

    @staticmethod
    def desktop_control_backend(name=None):
        """
        Possible backends:
           - autopy - Windows and Linux compatible with both the GUI actions and
                      their calls executed on the same machine.
           - qemu - guest OS independent with GUI actions on a virtual machine
                    through Qemu Monitor object (provided by Autotest) and
                    their calls on the host machine.
           - vncdotool - guest OS independent or Linux remote OS with GUI
                         actions on a remote machine through vnc and their
                         calls on a vnc client machine.

        Warning: To use a particular backend you need to satisfy its dependencies,
        i.e. the backend has to be installed or you will have unsatisfied imports.
        """
        if name == None:
            return Settings._desktop_control_backend
        else:
            Settings._desktop_control_backend = name

    # these methods do not check for valid values since this
    # is already done at the equalizer on initialization
    @staticmethod
    def find_image_backend(name=None):
        """
        Possible backends:
            - template - template matching using correlation coefficients,
                         square difference or the default autopy matching.
            - feature - feature matching using a mixture of feature detection,
                        extraction and matching algorithms.
            - hybrid - a mixture of template and feature matching where the
                       first is used as necessary and the second as sufficient stage.

        Warning: To use a particular backend you need to satisfy its dependencies,
        i.e. the backend has to be installed or you will have unsatisfied imports.
        """
        if name == None:
            return Settings._find_image_backend
        else:
            Settings._find_image_backend = name

    @staticmethod
    def template_match_backend(name=None):
        if name == None:
            return Settings._template_match_backend
        else:
            Settings._template_match_backend = name

    @staticmethod
    def feature_detect_backend(name=None):
        if name == None:
            return Settings._feature_detect_backend
        else:
            Settings._feature_detect_backend = name

    @staticmethod
    def feature_extract_backend(name=None):
        if name == None:
            return Settings._feature_extract_backend
        else:
            Settings._feature_extract_backend = name

    @staticmethod
    def feature_match_backend(name=None):
        if name == None:
            return Settings._feature_match_backend
        else:
            Settings._feature_match_backend = name
