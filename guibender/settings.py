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
    _click_delay = 0.1
    _drag_delay = 0.5
    _drop_delay = 0.5
    _keys_delay = 0.2
    _rescan_speed_on_find = 0.2
    _save_needle_on_error = True
    _image_logging_level = logging.ERROR
    _image_logging_destination = "."
    _image_logging_step_width = 3

    # backends shared between all instances
    _desktop_control_backend = "autopy-nix"
    _vnc_hostname = "localhost"
    _vnc_port = 0
    _find_image_backend = "hybrid"
    _template_match_backend = "ccoeff_normed"
    _feature_detect_backend = "ORB"
    _feature_extract_backend = "BRIEF"
    _feature_match_backend = "BruteForce-Hamming"

    @staticmethod
    def click_delay(delay=None):
        """Timeout before mouse click."""
        if delay == None:
            return Settings._click_delay
        else:
            Settings._click_delay = delay

    @staticmethod
    def delay_after_drag(delay=None):
        """Timeout before drag operation."""
        if delay == None:
            return Settings._drag_delay
        else:
            Settings._drag_delay = delay

    @staticmethod
    def delay_before_drop(delay=None):
        """Timeout before drop operation."""
        if delay == None:
            return Settings._drop_delay
        else:
            Settings._drop_delay = delay

    @staticmethod
    def delay_before_keys(delay=None):
        """Timeout before key press operation."""
        if delay == None:
            return Settings._keys_delay
        else:
            Settings._keys_delay = delay

    @staticmethod
    def rescan_speed_on_find(delay=None):
        """
        Frequency of the image matching attempts (to reduce overhead on the CPU).
        """
        if delay == None:
            return Settings._rescan_speed_on_find
        else:
            Settings._rescan_speed_on_find = delay

    @staticmethod
    def save_needle_on_error(value=None):
        """
        Perform an extra dump of the needle on matching error.
        """
        if value == None:
            return Settings._save_needle_on_error
        elif value == True or value == False:
            Settings._save_needle_on_error = value
        else:
            raise ValueError

    @staticmethod
    def image_logging_level(level=None):
        """
        Possible values: similar to the python logging module.

        See the image logging documentation for more details.
        """
        if level == None:
            return Settings._image_logging_level
        else:
            Settings._image_logging_level = level

    @staticmethod
    def image_logging_destination(dest=None):
        """
        String for relative path of the image logging steps.
        """
        if dest == None:
            return Settings._image_logging_destination
        else:
            Settings._image_logging_destination = dest

    @staticmethod
    def image_logging_step_width(width=None):
        """
        Integer to determine the number of digits when enumerating the image
        logging steps, e.g. width=3 for 001, 002, etc.
        """
        if width == None:
            return Settings._image_logging_step_width
        else:
            Settings._image_logging_step_width = width

    @staticmethod
    def desktop_control_backend(name=None):
        """
        Possible backends:
           - autopy-win, autopy-nix - Windows, Linux (and OS X) compatible with
                                      both the GUI actions and their calls
                                      executed on the same machine.
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
            if name not in ["autopy-win", "autopy-nix", "qemu", "vncdotool"]:
                raise ValueError("Unsupported backend for GUI actions '%s'" % name)
            Settings._desktop_control_backend = name

    @staticmethod
    def vnc_hostname(name=None):
        """
        Hostname of the vnc server in case vncdotool backend is used.
        """
        if name == None:
            return Settings._vnc_hostname
        else:
            Settings._vnc_hostname = name

    @staticmethod
    def vnc_port(port=None):
        """
        Port of the vnc server in case vncdotool backend is used.
        """
        if port == None:
            return Settings._vnc_port
        else:
            Settings._vnc_port = port

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
        """
        Possible backends: autopy, sqdiff, ccorr, ccoeff, sqdiff_normed,
        ccorr_normed, ccoeff_normed.
        """
        if name == None:
            return Settings._template_match_backend
        else:
            Settings._template_match_backend = name

    @staticmethod
    def feature_detect_backend(name=None):
        """
        Possible backends: BruteForce, BruteForce-L1, BruteForce-Hamming,
        BruteForce-Hamming(2), in-house-raw, in-house-region.
        """
        if name == None:
            return Settings._feature_detect_backend
        else:
            Settings._feature_detect_backend = name

    @staticmethod
    def feature_extract_backend(name=None):
        """
        Possible backends: ORB, FAST, STAR, GFTT, HARRIS, Dense, oldSURF.
        """
        if name == None:
            return Settings._feature_extract_backend
        else:
            Settings._feature_extract_backend = name

    @staticmethod
    def feature_match_backend(name=None):
        """
        Possible backends: ORB, BRIEF, FREAK.
        """
        if name == None:
            return Settings._feature_match_backend
        else:
            Settings._feature_match_backend = name
