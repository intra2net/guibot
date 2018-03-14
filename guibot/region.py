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

import time
import os

# interconnected classes - carefully avoid circular reference
from config import GlobalConfig
from location import Location
from imagelogger import ImageLogger
from errors import *
from target import *
from finder import *
from desktopcontrol import *

import logging
log = logging.getLogger('guibot.region')


class Region(object):
    """
    Region of the screen supporting vertex and nearby region selection,
    validation of expected images, and mouse and keyboard control.
    """

    def __init__(self, xpos=0, ypos=0, width=0, height=0,
                 dc=None, cv=None):
        """
        Build a region object from upleft to downright vertex coordinates.

        :param int xpos: x coordinate of the upleft vertex of the region
        :param int ypos: y coordinate of the upleft vertex of the region
        :param int width: width of the region (xpos+width for downright vertex x)
        :param int height: height of the region (ypos+height for downright vertex y)
        :param dc: DC backend used for any desktop control
        :type dc: :py:class:`desktopcontrol.DesktopControl` or None
        :param cv: CV backend used for any target finding
        :type cv: :py:class:`finder.Finder` or None
        :raises: :py:class:`UninitializedBackendError` if the region is empty

        If any of the backends is not defined a new one will be initiated
        using the parameters defined in :py:class:`config.GlobalConfig`.
        If `width` or `height` remains zero, it will be set to the maximum
        available within the screen space.
        """
        if dc is None:
            if GlobalConfig.desktop_control_backend == "autopy":
                dc = AutoPyDesktopControl()
            elif GlobalConfig.desktop_control_backend == "qemu":
                dc = QemuDesktopControl()
            elif GlobalConfig.desktop_control_backend == "vncdotool":
                dc = VNCDoToolDesktopControl()
        if cv is None:
            if GlobalConfig.find_backend == "autopy":
                cv = AutoPyFinder()
            elif GlobalConfig.find_backend == "contour":
                cv = ContourFinder()
            elif GlobalConfig.find_backend == "template":
                cv = TemplateFinder()
            elif GlobalConfig.find_backend == "feature":
                cv = FeatureFinder()
            elif GlobalConfig.find_backend == "cascade":
                cv = CascadeFinder()
            elif GlobalConfig.find_backend == "text":
                cv = TextFinder()
            elif GlobalConfig.find_backend == "tempfeat":
                cv = TemplateFeatureFinder()
            elif GlobalConfig.find_backend == "deep":
                cv = DeepFinder()
            elif GlobalConfig.find_backend == "hybrid":
                cv = HybridFinder()

        # since the backends are read/write make them public attributes
        self.dc_backend = dc
        self.cv_backend = cv
        self.default_target_type = Image

        self._last_match = None
        self._xpos = xpos
        self._ypos = ypos

        # zero width/height implies the one of the available screen
        if width == 0 and self.dc_backend.width != 0:
            self._width = self.dc_backend.width
        else:
            self._width = width
        if height == 0 and self.dc_backend.height != 0:
            self._height = self.dc_backend.height
        else:
            self._height = height
        # clipping should only be performed on initialized screen
        if self.dc_backend.width != 0 and self.dc_backend.height != 0:
            self._ensure_screen_clipping()

        mouse_map = self.dc_backend.mousemap
        for mouse_button in dir(mouse_map):
            if mouse_button.endswith('_BUTTON'):
                setattr(self, mouse_button, getattr(mouse_map, mouse_button))

        key_map = self.dc_backend.keymap
        for key in dir(key_map):
            if not key.startswith('__') and key != "to_string":
                setattr(self, key, getattr(key_map, key))

        mod_map = self.dc_backend.modmap
        for modifier_key in dir(mod_map):
            if modifier_key.startswith('MOD_'):
                setattr(self, modifier_key, getattr(mod_map, modifier_key))

    def _ensure_screen_clipping(self):
        screen_width = self.dc_backend.width
        screen_height = self.dc_backend.height

        if self._xpos < 0:
            self._xpos = 0

        if self._ypos < 0:
            self._ypos = 0

        if self._xpos > screen_width:
            self._xpos = screen_width - 1

        if self._ypos > screen_height:
            self._ypos = screen_height - 1

        if self._xpos + self._width > screen_width:
            self._width = screen_width - self._xpos

        if self._ypos + self._height > screen_height:
            self._height = screen_height - self._ypos

    def get_x(self):
        """
        Getter for readonly attribute.

        :returns: x coordinate of the upleft vertex of the region
        :rtype: int
        """
        return self._xpos
    x = property(fget=get_x)

    def get_y(self):
        """
        Getter for readonly attribute.

        :returns: y coordinate of the upleft vertex of the region
        :rtype: int
        """
        return self._ypos
    y = property(fget=get_y)

    def get_width(self):
        """
        Getter for readonly attribute.

        :returns: width of the region (xpos+width for downright vertex x)
        :rtype: int
        """
        return self._width
    width = property(fget=get_width)

    def get_height(self):
        """
        Getter for readonly attribute.

        :returns: height of the region (ypos+height for downright vertex y)
        :rtype: int
        """
        return self._height
    height = property(fget=get_height)

    def get_center(self):
        """
        Getter for readonly attribute.

        :returns: center of the region
        :rtype: :py:class:`location.Location`
        """
        xpos = self._xpos + self._width / 2
        ypos = self._ypos + self._height / 2

        return Location(xpos, ypos)
    center = property(fget=get_center)

    def get_top_left(self):
        """
        Getter for readonly attribute.

        :returns: upleft vertex of the region
        :rtype: :py:class:`location.Location`
        """
        return Location(self._xpos, self._ypos)
    top_left = property(fget=get_top_left)

    def get_top_right(self):
        """
        Getter for readonly attribute.

        :returns: upright vertex of the region
        :rtype: :py:class:`location.Location`
        """
        return Location(self._xpos + self._width, self._ypos)
    top_right = property(fget=get_top_right)

    def get_bottom_left(self):
        """
        Getter for readonly attribute.

        :returns: downleft vertex of the region
        :rtype: :py:class:`location.Location`
        """
        return Location(self._xpos, self._ypos + self._height)
    bottom_left = property(fget=get_bottom_left)

    def get_bottom_right(self):
        """
        Getter for readonly attribute.

        :returns: downright vertex of the region
        :rtype: :py:class:`location.Location`
        """
        return Location(self._xpos + self._width, self._ypos + self._height)
    bottom_right = property(fget=get_bottom_right)

    def is_empty(self):
        """
        Getter for readonly attribute.

        :returns: whether the region is empty, i.e. has zero size
        :rtype: bool
        """
        return self._width == 0 and self._height == 0
    is_empty = property(fget=is_empty)

    def get_last_match(self):
        """
        Getter for readonly attribute.

        :returns: last match obtained from finding a target within the region
        :rtype: :py:class:`match.Match`
        """
        return self._last_match
    last_match = property(fget=get_last_match)

    def get_mouse_location(self):
        """
        Getter for readonly attribute.

        :returns: mouse location
        :rtype: :py:class:`location.Location`
        """
        return self.dc_backend.get_mouse_location()
    mouse_location = property(fget=get_mouse_location)

    """Main region methods"""
    def nearby(self, rrange=50):
        """
        Obtain a region containing the previous one but enlarged
        by a number of pixels on each side.

        :param int rrange: number of pixels to add
        :returns: new region enlarged by `rrange` on all sides
        :rtype: :py:class:`Region`
        """
        log.debug("Checking nearby the current region")
        new_xpos = self._xpos - rrange
        if new_xpos < 0:
            new_xpos = 0

        new_ypos = self._ypos - rrange
        if new_ypos < 0:
            new_ypos = 0

        new_width = self._width + rrange + self._xpos - new_xpos
        new_height = self._height + rrange + self._ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, new_ypos, new_width, new_height,
                      self.dc_backend, self.cv_backend)

    def above(self, rrange=0):
        """
        Obtain a region containing the previous one but enlarged
        by a number of pixels on the upper side.

        :param int rrange: number of pixels to add
        :returns: new region enlarged by `rrange` on upper side
        :rtype: :py:class:`Region`
        """
        log.debug("Checking above the current region")
        if rrange == 0:
            new_ypos = 0
            new_height = self._ypos + self._height
        else:
            new_ypos = self._ypos - rrange
            if new_ypos < 0:
                new_ypos = 0

            new_height = self._height + self._ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(self._xpos, new_ypos, self._width, new_height,
                      self.dc_backend, self.cv_backend)

    def below(self, rrange=0):
        """
        Obtain a region containing the previous one but enlarged
        by a number of pixels on the lower side.

        :param int rrange: number of pixels to add
        :returns: new region enlarged by `rrange` on lower side
        :rtype: :py:class:`Region`
        """
        log.debug("Checking below the current region")
        if rrange == 0:
            rrange = self.dc_backend.height

        new_height = self._height + rrange

        # Final clipping is done in the Region constructor
        return Region(self._xpos, self._ypos, self._width, new_height,
                      self.dc_backend, self.cv_backend)

    def left(self, rrange=0):
        """
        Obtain a region containing the previous one but enlarged
        by a number of pixels on the left side.

        :param int rrange: number of pixels to add
        :returns: new region enlarged by `rrange` on left side
        :rtype: :py:class:`Region`
        """
        log.debug("Checking left of the current region")
        if rrange == 0:
            new_xpos = 0
            new_width = self._xpos + self._width
        else:
            new_xpos = self._xpos - rrange
            if new_xpos < 0:
                new_xpos = 0

            new_width = self._width + self._xpos - new_xpos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, self._ypos, new_width, self._height,
                      self.dc_backend, self.cv_backend)

    def right(self, rrange=0):
        """
        Obtain a region containing the previous one but enlarged
        by a number of pixels on the right side.

        :param int rrange: number of pixels to add
        :returns: new region enlarged by `rrange` on right side
        :rtype: :py:class:`Region`
        """
        log.debug("Checking right of the current region")
        if rrange == 0:
            rrange = self.dc_backend.width

        new_width = self._width + rrange

        # Final clipping is done in the Region constructor
        return Region(self._xpos, self._ypos, new_width, self._height,
                      self.dc_backend, self.cv_backend)

    """Image expect methods"""
    def find(self, target, timeout=10):
        """
        Find a target (image, text, etc.) on the screen.

        :param target: target to look for
        :type target: str or :py:class:`target.Target`
        :param int timeout: timeout before giving up
        :returns: match obtained from finding the target within the region
        :rtype: :py:class:`match.Match`
        :raises: :py:class:`errors.FindError` if no match is found

        This method is the main entrance to all our target finding capabilities
        and is the milestone for all target expect methods.
        """
        if isinstance(target, basestring):
            target = self._target_from_string(target)
        log.debug("Looking for target %s", target)
        cv_backend = self._determine_cv_backend(target)
        dc_backend = self.dc_backend

        timeout_limit = time.time() + timeout
        while True:
            screen_capture = dc_backend.capture_screen(self)

            found_pics = cv_backend.find(target, screen_capture)
            if len(found_pics) > 0:
                from match import Match
                match = found_pics[0]
                self._last_match = Match(match.x+self.x, match.y+self.y,
                                         match.width, match.height, match.dx, match.dy,
                                         match.similarity, dc=dc_backend, cv=cv_backend)
                return self._last_match

            elif time.time() > timeout_limit:
                if GlobalConfig.save_needle_on_error:
                    if not os.path.exists(ImageLogger.logging_destination):
                        os.mkdir(ImageLogger.logging_destination)
                    dump_path = GlobalConfig.image_logging_destination
                    hdump_path = os.path.join(dump_path, "last_finderror_haystack.png")
                    ndump_path = os.path.join(dump_path, "last_finderror_needle.png")
                    screen_capture.save(hdump_path)
                    target.save(ndump_path)
                raise FindError(target)

            else:
                # don't hog the CPU
                time.sleep(GlobalConfig.rescan_speed_on_find)

    def find_all(self, target, timeout=10, allow_zero=False):
        """
        Find multiples of a target on the screen.

        :param target: target to look for
        :type target: str or :py:class:`target.Target`
        :param int timeout: timeout before giving up
        :param bool allow_zero: whether to allow zero matches or raise error
        :returns: matches obtained from finding the target within the region
        :rtype: [:py:class:`match.Match`]
        :raises: :py:class:`errors.FindError` if no matches are found
                 and zero matches are not allowed

        This method is similar the one above but allows for more than one match.
        """
        if isinstance(target, basestring):
            target = self._target_from_string(target)
        log.debug("Looking for target %s", target)
        cv_backend = self._determine_cv_backend(target)
        dc_backend = self.dc_backend

        # TODO: decide about updating the last_match attribute
        last_matches = []
        timeout_limit = time.time() + timeout
        while True:
            screen_capture = dc_backend.capture_screen(self)

            found_pics = cv_backend.find(target, screen_capture)
            if len(found_pics) > 0:
                from match import Match
                for match in found_pics:
                    last_matches.append(Match(match.x+self.x, match.y+self.y,
                                              match.width, match.height, match.dx, match.dy,
                                              match.similarity, dc=dc_backend, cv=cv_backend))
                self._last_match = last_matches[-1]
                return last_matches

            elif time.time() > timeout_limit:
                if allow_zero:
                    return last_matches
                else:
                    if GlobalConfig.save_needle_on_error:
                        log.info("Dumping the haystack at /tmp/guibot_last_finderror.png")
                        screen_capture.save('/tmp/guibot_last_finderror.png')
                        target.save('/tmp/guibot_last_finderror_needle.png')
                    raise FindError(target)

            else:
                # don't hog the CPU
                time.sleep(GlobalConfig.rescan_speed_on_find)

    def _target_from_string(self, target_str):
        # handle some specific target types
        try:
            # guess from a match file has the highest precedence
            return Target.from_match_file(target_str)
        except (IOError, FileNotFoundError) as ex:
            log.debug(ex)
            try:
                # if a match file does not exist but a data file exists
                return Target.from_data_file(target_str)
            except (IncompatibleTargetFileError, FileNotFoundError) as ex:
                log.debug(ex)
                # if anything else goes wrong fail on the default type
                return self.default_target_type(target_str)

    def _determine_cv_backend(self, target):
        if target.use_own_settings:
            log.debug("Using special settings to match %s", target)
            return target.match_settings
        if isinstance(target, Text) and not isinstance(self.cv_backend, TextFinder):
            raise IncompatibleTargetError("Need text matcher for matching text")
        if isinstance(target, Pattern) and not (isinstance(self.cv_backend, CascadeFinder) or
                                               isinstance(self.cv_backend, DeepFinder)):
            raise IncompatibleTargetError("Need pattern matcher for matching patterns")
        if isinstance(target, Chain) and not isinstance(self.cv_backend, HybridFinder):
            raise IncompatibleTargetError("Need hybrid matcher for matching chain targets")
        target.match_settings = self.cv_backend
        return self.cv_backend

    def sample(self, target):
        """
        Sample the similarity between a target and the screen,
        i.e. an empirical probability that the target is on the screen.

        :param target: target to look for
        :type target: str or :py:class:`target.Target`
        :returns: similarity with best match on the screen
        :rtype: float

        .. note:: Not all matchers support a 'similarity' value. The ones that don't
            will return zero similarity (similarly to the target logging case).
        """
        log.debug("Looking for target %s", target)
        if isinstance(target, basestring):
            target = Image(target)
        if not target.use_own_settings:
            target.match_settings = self.cv_backend
            target.use_own_settings = True
        target = target.with_similarity(0.0)
        match = self.find(target)
        similarity = match.similarity
        return similarity

    def exists(self, target, timeout=0):
        """
        Check if a target exists on the screen using the matching
        success as a threshold for the existence.

        :param target: target to look for
        :type target: str or :py:class:`target.Target`
        :param int timeout: timeout before giving up
        :returns: match obtained from finding the target within the region
                  or nothing if no match is found
        :rtype: :py:class:`match.Match` or None
        """
        log.debug("Checking if %s is present", target)
        try:
            return self.find(target, timeout)
        except FindError:
            pass
        return None

    def wait(self, target, timeout=30):
        """
        Wait for a target to appear (be matched) with a given timeout
        as failing tolerance.

        :param target: target to look for
        :type target: str or :py:class:`target.Target`
        :param int timeout: timeout before giving up
        :returns: match obtained from finding the target within the region
        :rtype: :py:class:`match.Match`
        :raises: :py:class:`errors.FindError` if no match is found
        """
        log.info("Waiting for %s", target)
        return self.find(target, timeout)

    def wait_vanish(self, target, timeout=30):
        """
        Wait for a target to disappear (be unmatched, i.e. matched
        without success) with a given timeout as failing tolerance.

        :param target: target to look for
        :type target: str or :py:class:`target.Target`
        :param int timeout: timeout before giving up
        :returns: whether the target disappeared from the region
        :rtype: bool
        :raises: :py:class:`errors.NotFindError` if match is still found
        """
        log.info("Waiting for %s to vanish", target)
        expires = time.time() + timeout
        while time.time() < expires:
            if self.exists(target, 0) is None:
                return True

            # don't hog the CPU
            time.sleep(0.2)

        # target is still there
        raise NotFindError(target)

    """Mouse methods"""
    def idle(self, timeout):
        """
        Wait for a number of seconds and continue the nested call chain.

        :param int timeout: timeout to wait for
        :returns: self
        :rtype: :py:class:`Region`

        This method can be used as both a way to compactly wait for some time
        while not breaking the call chain. e.g.::

            aregion.hover('abox').idle(1).click('aboxwithinthebox')

        and as a way to conveniently perform timeout in between actions.
        """
        log.debug("Waiting for %ss", timeout)
        time.sleep(timeout)
        return self

    def hover(self, target_or_location):
        """
        Hover the mouse over a target or location.

        :param target_or_location: target or location to hover to
        :type target_or_location: :py:class:`match.Match` or :py:class:`location.Location` or
                                 str or :py:class:`target.Target`
        :returns: match from finding the target or nothing if hovering over a known location
        :rtype: :py:class:`match.Match` or None
        """
        log.info("Hovering over %s", target_or_location)
        smooth = GlobalConfig.smooth_mouse_drag

        # Handle Match
        from match import Match
        if isinstance(target_or_location, Match):
            self.dc_backend.mouse_move(target_or_location.target, smooth)
            return None

        # Handle Location
        if isinstance(target_or_location, Location):
            self.dc_backend.mouse_move(target_or_location, smooth)
            return None

        # Find target (image, text, pattern) or str
        match = self.find(target_or_location)
        self.dc_backend.mouse_move(match.target, smooth)

        return match

    def click(self, target_or_location, modifiers=None):
        """
        Click on a target or location using the left mouse button and
        optionally holding special keys.

        :param target_or_location: target or location to click on
        :type target_or_location: :py:class:`match.Match` or :py:class:`location.Location` or
                                 str or :py:class:`target.Target`
        :param modifiers: special keys to hold during clicking
                         (see :py:class:`inputmap.KeyModifier` for extensive list)
        :type modifiers: [str]
        :returns: match from finding the target or nothing if clicking on a known location
        :rtype: :py:class:`match.Match` or None

        The special keys refer to a list of key modifiers, e.g.::

            self.click('my_target', [KeyModifier.MOD_CTRL, 'x']).
        """
        match = self.hover(target_or_location)
        log.info("Clicking at %s", target_or_location)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
        self.dc_backend.mouse_click(self.LEFT_BUTTON, 1, modifiers)
        return match

    def right_click(self, target_or_location, modifiers=None):
        """
        Click on a target or location using the right mouse button and
        optionally holding special keys.

        Arguments and return values are analogical to :py:func:`Region.click`.
        """
        match = self.hover(target_or_location)
        log.info("Right clicking at %s", target_or_location)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
        self.dc_backend.mouse_click(self.RIGHT_BUTTON, 1, modifiers)
        return match

    def double_click(self, target_or_location, modifiers=None):
        """
        Double click on a target or location using the left mouse button
        and optionally holding special keys.

        Arguments and return values are analogical to :py:func:`Region.click`.
        """
        match = self.hover(target_or_location)
        log.info("Double clicking at %s", target_or_location)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
        self.dc_backend.mouse_click(self.LEFT_BUTTON, 2, modifiers)
        return match

    def multi_click(self, target_or_location, count=3, modifiers=None):
        """
        Click N times on a target or location using the left mouse button
        and optionally holding special keys.

        Arguments and return values are analogical to :py:func:`Region.click`.
        """
        match = self.hover(target_or_location)
        log.info("Clicking %s times at %s", count, target_or_location)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
        self.dc_backend.mouse_click(self.LEFT_BUTTON, count, modifiers)
        return match

    def click_expect(self, click_image_or_location,
                     expect_image_or_location=None,
                     modifiers=None, timeout=60):
        """
        Click on an image or location and wait for another one to appear.

        :param click_image_or_location: image or location to click on
        :type click_image_or_location: Image or Location
        :param expect_image_or_location: image or location to wait for
        :type expect_image_or_location: Image or Location or None
        :param modifiers: key modifiers when clicking
        :type modifiers: [Key] or None
        :param int timout: time in seconds to wait for
        :returns: match obtained from finding the second target within the region
        :rtype: :py:class:`match.Match`
        """
        self.click(click_image_or_location, modifiers=modifiers)
        if expect_image_or_location is None:
            expect_image_or_location = click_image_or_location
        return self.wait(expect_image_or_location, timeout)

    def click_vanish(self, click_image_or_location,
                     expect_image_or_location=None,
                     modifiers=None, timeout=60):
        """
        Click on an image or location and wait for another one to disappear.

        :param click_image_or_location: image or location to click on
        :type click_image_or_location: Image or Location
        :param expect_image_or_location: image or location to wait for
        :type expect_image_or_location: Image or Location or None
        :param modifiers: key modifiers when clicking
        :type modifiers: [Key] or None
        :param int timout: time in seconds to wait for
        :returns: whether the second target disappeared from the region
        :rtype: bool
        """
        self.click(click_image_or_location, modifiers=modifiers)
        if expect_image_or_location is None:
            expect_image_or_location = click_image_or_location
        return self.wait_vanish(expect_image_or_location, timeout)

    def click_at_index(self, anchor, index=0, find_number=3, timeout=10):
        """
        Find all instances of an anchor image and click on the one with the
        desired index given that they are horizontally then vertically sorted.

        :param str anchor: image to find all matches of
        :param int index: index of the match to click on (assuming >=1 matches),
            sorted according to their (x,y) coordinates
        :param int find_number: expected number of matches which is necessary
            for fast failure in case some elements are not visualized and/or
            proper matching result
        :param int timeout: timeout before which the number of matches should be found
        :returns: match from finding the target of the desired index
        :rtype: :py:class:`match.Match`

        .. note:: This method is a good replacement of a number of coincident
            limitations regarding the Windows version of autopy and Pyro and
            therefore the (Windows) virtual user:

            * autopy has an old BUG regarding capturing the screen at a region
              with boundaries, different than the entire screen -> subregioning which
              is the main way to deal with any kind of highly repeating and homogeneous
              interface, is totally unavailable here.
            * Pyro4 cannot serialize generators, so this is an implementation of a
              "generator step" involving clicking on consecutive matches.
            * The serialized virtual user now returns a list of proxified matches
              when calling find_all, but they are all essentially useless as they
              don't proxify their returned objects and cannot be sent back as arguments.
              The special proxy interface of the virtual user was implemented only to
              handle the most basic case - serialize the objects returned by the main
              shared class by proxifying them (turning them into remote objects as well,
              which already have a well-defined serialization method) and nothing more.
        """
        matched = False
        for _ in range(timeout):
            targets = self.find_all(anchor)
            if len(targets) == find_number:
                matched = True
                break
        if not matched:
            # raise an error without redundant imports
            self.find(anchor)

        sorted_targets = sorted(targets, key=lambda x: (x.x, x.y))
        logging.debug("Totally %s clicking matches found: %s", len(sorted_targets),
                      ["(%s, %s)" % (x.x, x.y) for x in sorted_targets])
        self.click(sorted_targets[index])
        return sorted_targets[index]

    def mouse_down(self, target_or_location, button=None):
        """
        Hold down an arbitrary mouse button on a target or location.

        :param target_or_location: target or location to toggle on
        :type target_or_location: :py:class:`match.Match` or :py:class:`location.Location` or
                                 str or :py:class:`target.Target`
        :param button: button index depending on backend (default is left button)
                       (see :py:class:`inputmap.MouseButton` for extensive list)
        :type button: int or None
        :returns: match from finding the target or nothing if toggling on a known location
        :rtype: :py:class:`match.Match` or None
        """
        if button is None:
            button = self.LEFT_BUTTON
        match = self.hover(target_or_location)
        log.debug("Holding down the mouse at %s", target_or_location)
        self.dc_backend.mouse_down(button)
        return match

    def mouse_up(self, target_or_location, button=None):
        """
        Release an arbitrary mouse button on a target or location.

        :param target_or_location: target or location to toggle on
        :type target_or_location: :py:class:`match.Match` or :py:class:`location.Location` or
                                 str or :py:class:`target.Target`
        :param button: button index depending on backend (default is left button)
                       (see :py:class:`inputmap.MouseButton` for extensive list)
        :type button: int or None
        :returns: match from finding the target or nothing if toggling on a known location
        :rtype: :py:class:`match.Match` or None
        """
        if button is None:
            button = self.LEFT_BUTTON
        match = self.hover(target_or_location)
        log.debug("Holding up the mouse at %s", target_or_location)
        self.dc_backend.mouse_up(button)
        return match

    def drag_drop(self, src_target_or_location, dst_target_or_location, modifiers=None):
        """
        Drag from and drop at a target or location optionally holding special keys.

        :param src_target_or_location: target or location to drag from
        :type src_target_or_location: :py:class:`match.Match` or :py:class:`location.Location` or
                                     str or :py:class:`target.Target`
        :param dst_target_or_location: target or location to drop at
        :type dst_target_or_location: :py:class:`match.Match` or :py:class:`location.Location` or
                                     str or :py:class:`target.Target`
        :param modifiers: special keys to hold during dragging and dropping
                         (see :py:class:`inputmap.KeyModifier` for extensive list)
        :type modifiers: [str]
        :returns: match from finding the target or nothing if dropping at a known location
        :rtype: :py:class:`match.Match` or None
        """
        self.drag_from(src_target_or_location, modifiers)
        match = self.drop_at(dst_target_or_location, modifiers)
        return match

    def drag_from(self, target_or_location, modifiers=None):
        """
        Drag from a target or location optionally holding special keys.

        Arguments and return values are analogical to :py:func:`Region.drag_drop`
        but with `target_or_location` as `src_target_or_location`.
        """
        match = self.hover(target_or_location)

        time.sleep(0.2)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
            self.dc_backend.keys_toggle(modifiers, True)
            #self.dc_backend.keys_toggle(["Ctrl"], True)

        log.info("Dragging %s", target_or_location)
        self.dc_backend.mouse_down(self.LEFT_BUTTON)
        time.sleep(GlobalConfig.delay_after_drag)

        return match

    def drop_at(self, target_or_location, modifiers=None):
        """
        Drop at a target or location optionally holding special keys.

        Arguments and return values are analogical to :py:func:`Region.drag_drop`
        but with `target_or_location` as `dst_target_or_location`.
        """
        match = self.hover(target_or_location)
        time.sleep(GlobalConfig.delay_before_drop)

        log.info("Dropping at %s", target_or_location)
        self.dc_backend.mouse_up(self.LEFT_BUTTON)

        time.sleep(0.5)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
            self.dc_backend.keys_toggle(modifiers, False)

        return match

    """Keyboard methods"""
    def press_keys(self, keys):
        """
        Press a single key or a list of keys simultaneously.

        :param keys: characters or special keys depending on the backend
                     (see :py:class:`inputmap.Key` for extensive list)
        :type keys: [str] or str (possibly special keys in both cases)
        :returns: self
        :rtype: :py:class:`Region`

        Thus, the line ``self.press_keys([Key.ENTER])`` is equivalent to
        the line ``self.press_keys(Key.ENTER)``. Other examples are::

            self.press_keys([Key.CTRL, 'X'])
            self.press_keys(['a', 'b', 3])
        """
        keys_list = self._parse_keys(keys)
        time.sleep(GlobalConfig.delay_before_keys)
        self.dc_backend.keys_press(keys_list)
        return self

    def press_at(self, keys, target_or_location):
        """
        Press a single key or a list of keys simultaneously
        at a specified target or location.

        This method is similar to :py:func:`Region.press_keys` but
        with an extra argument like :py:func:`Region.click`.
        """
        keys_list = self._parse_keys(keys, target_or_location)
        match = self.click(target_or_location)
        time.sleep(GlobalConfig.delay_before_keys)
        self.dc_backend.keys_press(keys_list)
        return match

    def _parse_keys(self, keys, target_or_location=None):
        at_str = " at %s" % target_or_location if target_or_location else ""

        keys_list = []
        # if not a list (i.e. if a single key)
        if isinstance(keys, int) or isinstance(keys, basestring):
            key = keys
            try:
                log.info("Pressing key '%s'%s", self.dc_backend.keymap.to_string(key), at_str)
            # if not a special key (i.e. if a character key)
            except KeyError:
                if isinstance(key, int):
                    key = str(key)
                elif len(key) > 1:
                    raise # a key cannot be a string (text)
                log.info("Pressing key '%s'%s", key, at_str)
            keys_list.append(key)
        else:
            key_strings = []
            for key in keys:
                try:
                    key_strings.append(self.dc_backend.keymap.to_string(key))
                except KeyError:
                    if isinstance(key, int):
                        key = str(key)
                    elif len(key) > 1:
                        raise # a key cannot be a string (text)
                    key_strings.append(key)
                keys_list.append(key)
            log.info("Pressing together keys '%s'%s",
                     "'+'".join(keystr for keystr in key_strings),
                     at_str)
        return keys_list

    def type_text(self, text, modifiers=None):
        """
        Type a list of consecutive character keys (without special keys).

        :param text: characters or strings (independent of the backend)
        :type text: [str] or str (no special keys in both cases)
        :param modifiers: special keys to hold during typing
                         (see :py:class:`inputmap.KeyModifier` for extensive list)
        :type modifiers: [str]
        :returns: self
        :rtype: :py:class:`Region`

        Thus, the line ``self.type_text(['hello'])`` is equivalent to
        the line ``self.type_text('hello')``. Other examples are::

            self.type_text('ab3') # compare with press_keys()
            self.type_text(['Hello', ' ', 'user3614']) # in cases with appending

        Special keys are only allowed as modifiers here - simply call
        :py:func:`Region.press_keys` multiple times for consecutively
        typing special keys.
        """
        text_list = self._parse_text(text)
        time.sleep(GlobalConfig.delay_before_keys)
        if modifiers != None:
            if isinstance(modifiers, basestring):
                modifiers = [modifiers]
            log.info("Holding the modifiers '%s'", "'+'".join(modifiers))
        self.dc_backend.keys_type(text_list, modifiers)
        return self

    def type_at(self, text, target_or_location, modifiers=None):
        """
        Type a list of consecutive character keys (without special keys)
        at a specified target or location.

        This method is similar to :py:func:`Region.type_text` but
        with an extra argument like :py:func:`Region.click`.
        """
        text_list = self._parse_text(text, target_or_location)
        match = None
        if target_or_location != None:
            match = self.click(target_or_location)
        time.sleep(GlobalConfig.delay_before_keys)
        if modifiers != None:
            if isinstance(modifiers, basestring):
                modifiers = [modifiers]
            log.info("Holding the modifiers '%s'", "'+'".join(modifiers))
        self.dc_backend.keys_type(text_list, modifiers)
        return match

    def _parse_text(self, text, target_or_location=None):
        at_str = " at %s" % target_or_location if target_or_location else ""

        text_list = []
        if isinstance(text, basestring):
            log.info("Typing text '%s'%s", text, at_str)
            text_list = [text]
        else:
            for part in text:
                if isinstance(part, basestring):
                    log.info("Typing text '%s'%s", part, at_str)
                    text_list.append(part)
                elif isinstance(part, int):
                    log.info("Typing '%i'%s", part, at_str)
                    text_list.append(str(part))
                else:
                    raise ValueError("Unknown text character" % part)
        return text_list

    """Mixed (form) methods"""
    def fill_at(self, anchor, text, dx, dy,
                del_flag=True, esc_flag=True,
                mark_click="double"):
        """
        Fills a new text at a text box with variable content
        using an anchor image and a displacement from that image.

        :param str anchor: image of reference for the input field
        :param str text: text to fill in
        :param int dx: displacement from the anchor in the x direction
        :param int dy: displacement from the anchor in the y direction
        :param bool del_flag: whether to delete the highlighted text
        :param bool esc_flag: whether to escape any possible fill suggestions
        :param str mark_click: "single", "double", or "triple" click to highlight previous text
        :returns: self
        :rtype: :py:class:`Region`
        :raises: :py:class:`exceptions.ValueError` if `mark_click` is not acceptable value

        If the delete flag is set the previous content will be deleted or
        otherwise the new text will be added in the end of the current text.
        If the escape flag is set an escape will be pressed after typing
        in order to avoid any entry suggestions from a dropdown list that
        could cover important image matching areas.

        Since different interfaces behave differently, one might need a
        single, double or triple click to mark the already present text that
        has to be replaced.
        """
        # NOTE: handle cases of empty value no filling anything
        if not text:
            return
        from match import Match
        if isinstance(anchor, Match):
            start_loc = anchor.target
        else:
            start_loc = self.hover(anchor).target
        loc = Location(start_loc.x + dx, start_loc.y + dy)

        if mark_click == "double":
            self.double_click(loc)
        elif mark_click == "single":
            self.click(loc)
        elif mark_click == "triple":
            self.double_click(loc)
            self.click(loc)
        else:
            raise ValueError("Incorrect value '%s' for clicking behavior" % mark_click)

        if isinstance(text, basestring):
            text = [text]
        if del_flag:
            text.insert(0, self.DELETE)
        else:
            text.insert(0, self.RIGHT)
        if esc_flag:
            text.append(self.ESC)
        for part in text:
            try:
                key_str = self.dc_backend.keymap.to_string(part)
                self.press_keys(part)
            except KeyError:
                self.type_text(part)

        return self

    def select_at(self, anchor, image_or_index, dx, dy, dw=0, dh=0):
        """
        Select an option at a dropdown list using either an integer index
        or an option image if the order cannot be easily inferred.

        :param str anchor: image of reference for the input dropdown menu
        :param image_or_index: item image or item index
        :type image_or_index: str or int
        :param int dx: displacement from the anchor in the x direction
        :param int dy: displacement from the anchor in the y direction
        :param int dw: width to add to the displacement for an image search area
        :param int dh: height to add to the displacement for an image search area
        :returns: self
        :rtype: :py:class:`Region`

        It uses an anchor image which is rather constant and a displacement
        to locate the dropdown location. It moves down to the option if
        index is used where index 0 represents the current selection.

        To avoid the limitations of the index method, an image of the option
        can be provided and will be matched in the area with and under the
        dropdown list. This also handles cases where the option coincides
        with the previously selected option. For more details see the really
        cool note in the end of this method.
        """
        # NOTE: handle cases of empty value no filling anything
        if not image_or_index:
            return
        from match import Match
        if isinstance(anchor, Match):
            start_loc = anchor.target
        else:
            start_loc = self.hover(anchor).target
        loc = Location(start_loc.x + dx, start_loc.y + dy)
        self.click(loc)
        # make sure the dropdown options appear
        time.sleep(1)
        if isinstance(image_or_index, int):
            move_key = self.UP if image_or_index < 0 else self.DOWN
            for _ in range(abs(image_or_index)):
                # TODO: multiple DOWN in a single press call doesn't work
                self.press_keys([move_key])
            self.press_keys([self.ENTER])
        else:
            # NOTE: By definition, the dropdown list will be below and centered
            # at the clicking location that we obtain from the anchor image.
            # Therefore, we need to center the generated dropdown haystack around
            # the x of 'loc'. However, it is possible that the option is
            # already selected and cannot be matched among the dropdown options.
            # This can be handled if that option is matched at the dropdown box (by
            # the clicking location) where the already selected option is shown again in
            # a normal way. Therefore, we need to make sure that the entire dropdown
            # is in the haystack area. Since the height of any of the options varies,
            # we need to take the worst case scenario, i.e. the largest y distance
            # that we have to cover so that we don't cut away the dropdown box from
            # the dropdown haystack. This worst case is a minimal number of options
            # which is 0, implying empty space repeated in the dropdown box and the
            # list, therefore a total of 2 option heights spanning the haystack height.
            # The haystack y displacement relative to 'loc' is then 1/2*1/2*dh
            dropdown_haystack = Region(xpos=loc.x - dw / 2,
                                       ypos=loc.y - dh / 4,
                                       width=dw, height=dh,
                                       dc=self.dc_backend, cv=self.cv_backend)
            dropdown_haystack.click(image_or_index)

        return self
