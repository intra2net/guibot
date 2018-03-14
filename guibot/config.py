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

import re
import os
import logging
log = logging.getLogger('guibot.config')

from errors import *


class GlobalConfig(type):
    """
    Metaclass used for the definition of static properties (the settings).

    We overwrite the name of the class in order to avoid documenting
    all settings here and adding an empty actual class. Instead, the resulting
    documentation contains just the config class (using this as metaclass)
    and all settings respectively. In this way the front user should not worry
    about such implementation detail and simply use the provided properties.

    For those that like to think about it nonetheless: All methods of the
    resulting config class are therefore static since they are methods of
    a class object, i.e. a metaclass instance.
    """

    # operational parameters shared between all instances
    _click_delay = 0.1
    _drag_delay = 0.5
    _drop_delay = 0.5
    _keys_delay = 0.2
    _type_delay = 0.1
    _rescan_speed_on_find = 0.2
    _smooth_mouse_drag = True
    _screen_autoconnect = True
    _preprocess_special_chars = True
    _save_needle_on_error = True
    _image_logging_level = logging.ERROR
    _image_logging_destination = "./imglog"
    _image_logging_step_width = 3
    _image_quality = 3

    # backends shared between all instances
    _desktop_control_backend = "autopy"
    _find_backend = "hybrid"
    _contour_threshold_backend = "adaptive"
    _template_match_backend = "ccoeff_normed"
    _feature_detect_backend = "ORB"
    _feature_extract_backend = "ORB"
    _feature_match_backend = "BruteForce-Hamming"
    _text_detect_backend = "erstat"
    _text_ocr_backend = "tesseract"
    _hybrid_match_backend = "autopy"

    def click_delay(self, value=None):
        """
        Getter/setter for property attribute.

        :param value: time interval between two clicks in a double click
        :type value: float or None
        :returns: current value if no argument was passed otherwise only sets it
        :rtype: float or None
        """
        if value is None:
            return GlobalConfig._click_delay
        else:
            GlobalConfig._click_delay = value
    #: time interval between two clicks in a double click
    click_delay = property(fget=click_delay, fset=click_delay)

    def delay_after_drag(self, value=None):
        """
        Same as :py:func:`GlobalConfig.click_delay` but with

        :param value: timeout before drag operation
        """
        if value is None:
            return GlobalConfig._drag_delay
        else:
            GlobalConfig._drag_delay = value
    #: timeout before drag operation
    delay_after_drag = property(fget=delay_after_drag, fset=delay_after_drag)

    def delay_before_drop(self, value=None):
        """
        Same as :py:func:`GlobalConfig.click_delay` but with

        :param value: timeout before drop operation
        """
        if value is None:
            return GlobalConfig._drop_delay
        else:
            GlobalConfig._drop_delay = value
    #: timeout before drop operation
    delay_before_drop = property(fget=delay_before_drop, fset=delay_before_drop)

    def delay_before_keys(self, value=None):
        """
        Same as :py:func:`GlobalConfig.click_delay` but with

        :param value: timeout before key press operation
        """
        if value is None:
            return GlobalConfig._keys_delay
        else:
            GlobalConfig._keys_delay = value
    #: timeout before key press operation
    delay_before_keys = property(fget=delay_before_keys, fset=delay_before_keys)

    def delay_between_keys(self, value=None):
        """
        Same as :py:func:`GlobalConfig.click_delay` but with

        :param value: time interval between two consecutively typed keys
        """
        if value is None:
            return GlobalConfig._type_delay
        else:
            GlobalConfig._type_delay = value
    #: time interval between two consecutively typed keys
    delay_between_keys = property(fget=delay_between_keys, fset=delay_between_keys)

    def rescan_speed_on_find(self, value=None):
        """
        Same as :py:func:`GlobalConfig.click_delay` but with

        :param value: time interval between two image matching attempts
                      (used to reduce overhead on the CPU)
        """
        if value is None:
            return GlobalConfig._rescan_speed_on_find
        else:
            GlobalConfig._rescan_speed_on_find = value
    #: time interval between two image matching attempts (used to reduce overhead on the CPU)
    rescan_speed_on_find = property(fget=rescan_speed_on_find, fset=rescan_speed_on_find)

    def smooth_mouse_drag(self, value=None):
        """
        Getter/setter for property attribute.

        :param value: whether to move the mouse cursor to a location instantly or smoothly
        :type value: bool or None
        :returns: current value if no argument was passed otherwise only sets it
        :rtype: bool or None
        :raises: :py:class:`ValueError` if value is not boolean or None

        This is useful if a routine task has to be executed faster without
        supervision or the need of debugging.
        """
        if value is None:
            return GlobalConfig._smooth_mouse_drag
        elif value == True or value == False:
            GlobalConfig._smooth_mouse_drag = value
        else:
            raise ValueError
    #: whether to move the mouse cursor to a location instantly or smoothly
    smooth_mouse_drag = property(fget=smooth_mouse_drag, fset=smooth_mouse_drag)

    def screen_autoconnect(self, value=None):
        """
        Same as :py:func:`GlobalConfig.smooth_mouse_drag` but with

        :param value: whether to perform complete initialization of the
                      desktop control backend

        Complete initialization includes connecting to the backend (screen)
        selected in the :py:func:`GlobalConfig.desktop_control_backend`.

        If disabled, you have to connect before performing any GUI operations::

            region.dc_backend.connect_screen()

        The use of this is to allow you to perform some configuration first.
        """
        if value is None:
            return GlobalConfig._screen_autoconnect
        elif value == True or value == False:
            GlobalConfig._screen_autoconnect = value
        else:
            raise ValueError
    #: whether to perform complete initialization of the desktop control backend
    screen_autoconnect = property(fget=screen_autoconnect, fset=screen_autoconnect)

    def preprocess_special_chars(self, value=None):
        """
        Same as :py:func:`GlobalConfig.smooth_mouse_drag` but with

        :param value: whether to preprocess capital and special characters and
                      handle them internally

        .. warning:: The characters will be forcefully preprocessed for the
            autopy on linux (capital and special) and vncdotool (capital) backends.
        """
        if value is None:
            return GlobalConfig._preprocess_special_chars
        elif value == True or value == False:
            GlobalConfig._preprocess_special_chars = value
        else:
            raise ValueError
    #: whether to preprocess capital and special characters and handle them internally
    preprocess_special_chars = property(fget=preprocess_special_chars, fset=preprocess_special_chars)

    def save_needle_on_error(self, value=None):
        """
        Same as :py:func:`GlobalConfig.smooth_mouse_drag` but with

        :param value: whether to perform an extra needle dump on matching error
        """
        if value is None:
            return GlobalConfig._save_needle_on_error
        elif value == True or value == False:
            GlobalConfig._save_needle_on_error = value
        else:
            raise ValueError
    #: whether to perform an extra needle dump on matching error
    save_needle_on_error = property(fget=save_needle_on_error, fset=save_needle_on_error)

    def image_logging_level(self, value=None):
        """
        Getter/setter for property attribute.

        :param value: logging level similar to the python logging module
        :type value: int or None
        :returns: current value if no argument was passed otherwise only sets it
        :rtype: int or None

        .. seealso:: See the image logging documentation for more details.
        """
        if value is None:
            return GlobalConfig._image_logging_level
        else:
            GlobalConfig._image_logging_level = value
    #: logging level similar to the python logging module
    image_logging_level = property(fget=image_logging_level, fset=image_logging_level)

    def image_logging_step_width(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_level` but with

        :param value: number of digits when enumerating the image
                      logging steps, e.g. value=3 for 001, 002, etc.
        """
        if value is None:
            return GlobalConfig._image_logging_step_width
        else:
            GlobalConfig._image_logging_step_width = value
    #: number of digits when enumerating the image logging steps, e.g. value=3 for 001, 002, etc.
    image_logging_step_width = property(fget=image_logging_step_width, fset=image_logging_step_width)

    def image_quality(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_level` but with

        :param value: quality of the image dumps ranging from 0 for no compression
                      to 9 for maximum compression (used to save space and reduce
                      the disk space needed for image logging)
        """
        if value is None:
            return GlobalConfig._image_quality
        else:
            GlobalConfig._image_quality = value
    #: quality of the image dumps ranging from 0 for no compression to 9 for maximum compression
    # (used to save space and reduce the disk space needed for image logging)
    image_quality = property(fget=image_quality, fset=image_quality)

    def image_logging_destination(self, value=None):
        """
        Getter/setter for property attribute.

        :param value: relative path of the image logging steps
        :type value: str or None
        :returns: current value if no argument was passed otherwise only sets it
        :rtype: str or None
        """
        if value is None:
            return GlobalConfig._image_logging_destination
        else:
            GlobalConfig._image_logging_destination = value
    #: relative path of the image logging steps
    image_logging_destination = property(fget=image_logging_destination, fset=image_logging_destination)

    def desktop_control_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the desktop control backend
        :raises: :py:class:`ValueError` if value is not among the supported backends

        Supported backends:
           * autopy - Windows, Linux (and OS X) compatible with both the GUI
                      actions and their calls executed on the same machine.
           * qemu - guest OS independent with GUI actions on a virtual machine
                    through Qemu Monitor object (provided by Autotest) and
                    their calls on the host machine.
           * vncdotool - guest OS independent or Linux remote OS with GUI
                         actions on a remote machine through vnc and their
                         calls on a vnc client machine.

        .. warning:: To use a particular backend you need to satisfy its dependencies,
            i.e. the backend has to be installed or you will have unsatisfied imports.
        """
        if value is None:
            return GlobalConfig._desktop_control_backend
        else:
            if value not in ["autopy", "qemu", "vncdotool"]:
                raise ValueError("Unsupported backend for GUI actions '%s'" % value)
            GlobalConfig._desktop_control_backend = value
    #: name of the desktop control backend
    desktop_control_backend = property(fget=desktop_control_backend, fset=desktop_control_backend)

    # these methods do not check for valid values since this
    # is already done during region and target initialization
    def find_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the computer vision backend

        Supported backends:
            * autopy - simple bitmap matching provided by autopy
            * contour - contour matching using overall shape estimation
            * template - template matching using correlation coefficients,
                         square difference, etc.
            * feature - matching using a mixture of feature detection,
                        extraction and matching algorithms
            * cascade - matching using OpenCV pretrained Haar cascades
            * text - text matching using ERStat or custom text detection,
                     followed by tesseract or Hidden Markov Model OCR
            * tempfeat - a mixture of template and feature matching where the
                       first is used as necessary and the second as sufficient stage
            * deep - deep learning matching using convolutional neural network but
                     customizable to any type of deep neural network
            * hybrid - use a composite approach with any of the above methods
                       as matching steps in a fallback sequence

        .. warning:: To use a particular backend you need to satisfy its dependencies,
            i.e. the backend has to be installed or you will have unsatisfied imports.
        """
        if value is None:
            return GlobalConfig._find_backend
        else:
            GlobalConfig._find_backend = value
    #: name of the computer vision backend
    find_backend = property(fget=find_backend, fset=find_backend)

    def contour_threshold_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the contour threshold backend

        Supported backends: normal, adaptive, canny.
        """
        if value is None:
            return GlobalConfig._contour_threshold_backend
        else:
            GlobalConfig._contour_threshold_backend = value
    #: name of the contour threshold backend
    contour_threshold_backend = property(fget=contour_threshold_backend, fset=contour_threshold_backend)

    def template_match_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the template matching backend

        Supported backends: autopy, sqdiff, ccorr, ccoeff, sqdiff_normed,
        ccorr_normed, ccoeff_normed.
        """
        if value is None:
            return GlobalConfig._template_match_backend
        else:
            GlobalConfig._template_match_backend = value
    #: name of the template matching backend
    template_match_backend = property(fget=template_match_backend, fset=template_match_backend)

    def feature_detect_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the feature detection backend

        Supported  backends: BruteForce, BruteForce-L1, BruteForce-Hamming,
        BruteForce-Hamming(2), in-house-raw, in-house-region.
        """
        if value is None:
            return GlobalConfig._feature_detect_backend
        else:
            GlobalConfig._feature_detect_backend = value
    #: name of the feature detection backend
    feature_detect_backend = property(fget=feature_detect_backend, fset=feature_detect_backend)

    def feature_extract_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the feature extraction backend

        Supported backends: ORB, FAST, STAR, GFTT, HARRIS, Dense, oldSURF.
        """
        if value is None:
            return GlobalConfig._feature_extract_backend
        else:
            GlobalConfig._feature_extract_backend = value
    #: name of the feature extraction backend
    feature_extract_backend = property(fget=feature_extract_backend, fset=feature_extract_backend)

    def feature_match_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the feature matching backend

        Supported backends: ORB, BRIEF, FREAK.
        """
        if value is None:
            return GlobalConfig._feature_match_backend
        else:
            GlobalConfig._feature_match_backend = value
    #: name of the feature matching backend
    feature_match_backend = property(fget=feature_match_backend, fset=feature_match_backend)

    def text_detect_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the text detection backend

        Supported backends: erstat, contours, components.
        """
        if value is None:
            return GlobalConfig._text_detect_backend
        else:
            GlobalConfig._text_detect_backend = value
    #: name of the text detection backend
    text_detect_backend = property(fget=text_detect_backend, fset=text_detect_backend)

    def text_ocr_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the optical character recognition backend

        Supported backends: tesseract, hmm, beamSearch.
        """
        if value is None:
            return GlobalConfig._text_ocr_backend
        else:
            GlobalConfig._text_ocr_backend = value
    #: name of the optical character recognition backend
    text_ocr_backend = property(fget=text_ocr_backend, fset=text_ocr_backend)

    def hybrid_match_backend(self, value=None):
        """
        Same as :py:func:`GlobalConfig.image_logging_destination` but with

        :param value: name of the hybrid matching backend for unconfigured one-step targets

        Supported backends: all nonhybrid backends of :py:func:`GlobalConfig.find_backend`.
        """
        if value is None:
            return GlobalConfig._hybrid_match_backend
        else:
            GlobalConfig._hybrid_match_backend = value
    #: name of the hybrid matching backend for unconfigured one-step targets
    hybrid_match_backend = property(fget=hybrid_match_backend, fset=hybrid_match_backend)


class GlobalConfig(object):
    """
    Handler for default configuration present in all
    cases where no specific value is set.

    The methods of this class are shared among
    all of its instances.
    """
    __metaclass__ = GlobalConfig


class LocalConfig(object):
    """
    Container for the configuration of all desktop control and
    computer vision backends, responsible for making them behave
    according to the selected parameters as well as for providing
    information about them and the current parameters.
    """

    def __init__(self, configure=True, synchronize=True):
        """
        Build a container for the entire backend configuration.

        :param bool configure: whether to also generate configuration
        :param bool synchronize: whether to also apply configuration

        Available algorithms can be seen in the `algorithms` attribute
        whose keys are the algorithm types and values are the members of
        these types. The algorithm types are shortened as `categories`.

        A parameter can be accessed as follows (example)::

            print self.params["control"]["vnc_hostname"]
        """
        self.categories = {}
        self.algorithms = {}
        self.params = {}

        self.categories["type"] = "backend_types"
        self.algorithms["backend_types"] = ("cv", "dc")

        if configure:
            self.__configure_backend()
        if synchronize:
            self.__synchronize_backend()

    def __configure_backend(self, backend=None, category="type", reset=False):
        if category != "type":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            # reset makes no sense here since this is the base configuration
            pass
        if backend is None:
            backend = "cv"
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        self.params[category] = {}
        self.params[category]["backend"] = backend

    def configure_backend(self, backend=None, category="type", reset=False):
        """
        Generate configuration dictionary for a given backend.

        :param backend: name of a preselected backend, see `algorithms[category]`
        :type backend: str or None
        :param str category: category for the backend, see `algorithms.keys()`
        :param bool reset: whether to (re)set all parent configurations as well
        :raises: :py:class:`UnsupportedBackendError` if `backend` is not among
                 the supported backends for the category (and is not `None`) or
                 the category is not found
        """
        self.__configure_backend(backend, category, reset)

    def configure(self, reset=True):
        """
        Generate configuration dictionary for all backends.

        :param bool reset: whether to (re)set all parent configurations as well

        If multiple categories are available and just some of them are configured,
        the rest will be reset to defaults. To configure specific category without
        changing others, use :py:func:`configure`.
        """
        self.configure_backend(reset=reset)

    def __synchronize_backend(self, backend=None, category="type", reset=False):
        if category != "type":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            # reset makes no sense here since this is the base configuration
            pass
        # no backend object to sync to
        backend = "cv" if backend is None else backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

    def synchronize_backend(self, backend=None, category="type", reset=False):
        """
        Synchronize a category backend with the equalizer configuration.

        :param backend: name of a preselected backend, see `algorithms[category]`
        :type backend: str or None
        :param str category: category for the backend, see `algorithms.keys()`
        :param bool reset: whether to (re)sync all parent backends as well
        :raises: :py:class:`UnsupportedBackendError` if  the category is not found
        :raises: :py:class:`UninitializedBackendError` if there is no backend object
                 that is configured with and with the required name
        """
        self.__synchronize_backend(backend, category, reset)

    def synchronize(self, reset=True):
        """
        Synchronize all backends with the current configuration dictionary.

        :param bool reset: whether to (re)sync all parent backends as well
        """
        self.synchronize_backend(reset=reset)

