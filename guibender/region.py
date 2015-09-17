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
#
import time
import os

# interconnected classes - import only their modules
# to avoid circular reference
from settings import Settings
from desktopcontrol import DesktopControl
from inputmap import Key, MouseButton
from errors import *
from location import Location
from image import Image
from imagefinder import ImageFinder
from imagelogger import ImageLogger

import logging
log = logging.getLogger('guibender.region')


class Region(object):
    # Mouse buttons
    LEFT_BUTTON = MouseButton.LEFT_BUTTON
    RIGHT_BUTTON = MouseButton.RIGHT_BUTTON
    CENTER_BUTTON = MouseButton.CENTER_BUTTON

    def __init__(self, xpos=0, ypos=0, width=0, height=0):
        self.desktop = DesktopControl()
        self.imagefinder = ImageFinder()
        self.last_match = None

        self.xpos = xpos
        self.ypos = ypos

        if width == 0:
            self.width = self.desktop.get_width()
        else:
            self.width = width

        if height == 0:
            self.height = self.desktop.get_height()
        else:
            self.height = height

        self._ensure_screen_clipping()

    def _ensure_screen_clipping(self):
        screen_width = self.desktop.get_width()
        screen_height = self.desktop.get_height()

        if self.xpos < 0:
            self.xpos = 0

        if self.ypos < 0:
            self.ypos = 0

        if self.xpos > screen_width:
            self.xpos = screen_width - 1

        if self.ypos > screen_height:
            self.ypos = screen_height - 1

        if self.xpos + self.width > screen_width:
            self.width = screen_width - self.xpos

        if self.ypos + self.height > screen_height:
            self.height = screen_height - self.ypos

    def get_x(self):
        return self.xpos

    def get_y(self):
        return self.ypos

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_center(self):
        xpos = (self.width - self.xpos) / 2
        ypos = (self.height - self.ypos) / 2

        return Location(xpos, ypos)

    def get_top_left(self):
        return Location(self.xpos, self.ypos)

    def get_top_right(self):
        return Location(self.xpos + self.width, self.ypos)

    def get_bottom_left(self):
        return Location(self.xpos, self.ypos + self.height)

    def get_bottom_right(self):
        return Location(self.xpos + self.width, self.ypos + self.height)

    def nearby(self, rrange=50):
        log.debug("Checking nearby the current region")
        new_xpos = self.xpos - rrange
        if new_xpos < 0:
            new_xpos = 0

        new_ypos = self.ypos - rrange
        if new_ypos < 0:
            new_ypos = 0

        new_width = self.width + rrange + self.xpos - new_xpos
        new_height = self.height + rrange + self.ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, new_ypos, new_width, new_height)

    def above(self, rrange=0):
        log.debug("Checking above the current region")
        if rrange == 0:
            new_ypos = 0
            new_height = self.ypos + self.height
        else:
            new_ypos = self.ypos - rrange
            if new_ypos < 0:
                new_ypos = 0

            new_height = self.height + self.ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(self.xpos, new_ypos, self.width, new_height)

    def below(self, rrange=0):
        log.debug("Checking below the current region")
        if rrange == 0:
            rrange = self.desktop.get_height()

        new_height = self.height + rrange

        # Final clipping is done in the Region constructor
        return Region(self.xpos, self.ypos, self.width, new_height)

    def left(self, rrange=0):
        log.debug("Checking left of the current region")
        if rrange == 0:
            new_xpos = 0
            new_width = self.xpos + self.width
        else:
            new_xpos = self.xpos - rrange
            if new_xpos < 0:
                new_xpos = 0

            new_width = self.width + self.xpos - new_xpos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, self.ypos, new_width, self.height)

    def right(self, rrange=0):
        log.debug("Checking right of the current region")
        if rrange == 0:
            rrange = self.desktop.get_width()

        new_width = self.width + rrange

        # Final clipping is done in the Region constructor
        return Region(self.xpos, self.ypos, new_width, self.height)

    def get_last_match(self):
        return self.last_match

    def configure_find(self, find_image=None, template_match=None,
                       feature_detect=None, feature_extract=None,
                       feature_match=None):
        self.imagefinder.eq.configure_backend(find_image, template_match,
                                              feature_detect, feature_extract,
                                              feature_match)

    def find(self, image, timeout=10):
        if isinstance(image, basestring):
            image = Image(image)
        log.debug("Looking for image %s", image)

        timeout_limit = time.time() + timeout
        while True:
            screen_capture = self.desktop.capture_screen(self)

            found_pic = self.imagefinder.find(image, screen_capture)
            if found_pic is not None:
                self.last_match = match.Match(self.xpos + found_pic.get_x(),
                                              self.ypos + found_pic.get_y(), image)
                return self.last_match

            elif time.time() > timeout_limit:
                if Settings.save_needle_on_error():
                    if not os.path.exists(ImageLogger.logging_destination):
                        os.mkdir(ImageLogger.logging_destination)
                    dump_path = Settings.image_logging_destination()
                    hdump_path = os.path.join(dump_path, "last_finderror_haystack.png")
                    ndump_path = os.path.join(dump_path, "last_finderror_needle.png")
                    screen_capture.save(hdump_path)
                    image.save(ndump_path)
                raise FindError(image)

            else:
                # don't hog the CPU
                time.sleep(Settings.rescan_speed_on_find())

    def find_all(self, image, timeout=10, allow_zero=False):
        if isinstance(image, basestring):
            image = Image(image)
        log.debug("Looking for multiple occurrences of image %s", image)

        # TODO: decide about updating the last_match attribute
        last_matches = []
        timeout_limit = time.time() + timeout
        while True:
            screen_capture = self.desktop.capture_screen(self)

            found_pics = self.imagefinder.find(image, screen_capture, multiple=True)

            if len(found_pics) > 0:
                for found_pic in found_pics:
                    last_matches.append(match.Match(self.xpos + found_pic.get_x(),
                                                    self.ypos + found_pic.get_y(), image))
                return last_matches

            elif time.time() > timeout_limit:
                if allow_zero:
                    return last_matches
                else:
                    if Settings.save_needle_on_error():
                        log.info("Dumping the haystack at /tmp/guibender_last_finderror.png")
                        screen_capture.save('/tmp/guibender_last_finderror.png')
                        image.save('/tmp/guibender_last_finderror_needle.png')
                    raise FindError(image)

            else:
                # don't hog the CPU
                time.sleep(Settings.rescan_speed_on_find())

    def sample(self, image):
        log.debug("Looking for image %s", image)
        if isinstance(image, basestring):
            image = Image(image)
        image = image.with_similarity(0.0)
        image.use_own_settings = True
        ImageLogger.accumulate_logging = True
        self.find(image)
        ImageLogger.accumulate_logging = False
        similarity = self.imagefinder.imglog.similarities[-1]
        self.imagefinder.imglog.clear()
        return similarity

    def exists(self, image, timeout=0):
        log.debug("Checking if %s is present", image)
        try:
            return self.find(image, timeout)
        except FindError:
            pass
        return None

    def wait(self, image, timeout=30):
        log.info("Waiting for %s", image)
        return self.find(image, timeout)

    def wait_vanish(self, image, timeout=30):
        log.info("Waiting for %s to vanish", image)
        expires = time.time() + timeout
        while time.time() < expires:
            if self.exists(image, 0) is None:
                return True

            # don't hog the CPU
            time.sleep(0.2)

        # image is still there
        name = image if isinstance(image, basestring) else image.filename
        raise NotFindError(name)

    def idle(self, timeout):
        """
        Wait for a number of seconds and continue the nested call chain.

        This method can be used as both a way to compactly wait for some time
        while not breaking the call chain. e.g.

        aregion.hover('abox').idle(1).click('aboxwithinthebox')

        and as a way to conveniently perform timeout in between actions.
        """
        log.debug("Waiting for %ss", timeout)
        time.sleep(timeout)
        return self

    def get_mouse_location(self):
        """
        Obtain the mouse location as a Location object.
        """
        return self.desktop.get_mouse_location()

    def hover(self, image_or_location):
        """
        Hover the mouse over a Location, Match, Image or string (image name)
        object and return a resulting Match object in case of search.
        """
        log.info("Hovering over %s", image_or_location)

        # Handle Match
        try:
            self.desktop.mouse_move(image_or_location.get_target())
            return None
        except AttributeError:
            pass

        # Handle Location
        try:
            self.desktop.mouse_move(image_or_location)
            return None
        except AttributeError:
            pass

        # Find image
        match = self.find(image_or_location)
        self.desktop.mouse_move(match.get_target())

        return match

    def click(self, image_or_location, modifiers=None):
        """
        Click over a variety of object types (like hover) using
        the left mouse button and optionally holding special keys
        (a list of key modifiers, e.g. [KeyModifier.MOD_CTRL, 'x']).
        """
        match = self.hover(image_or_location)
        log.info("Clicking at %s", image_or_location)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
        self.desktop.mouse_click(modifiers)
        return match

    def right_click(self, image_or_location, modifiers=None):
        """
        Click over a variety of object types (like hover) using
        the right mouse button and optionally holding special keys
        (like click).
        """
        match = self.hover(image_or_location)
        log.info("Right clicking at %s", image_or_location)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
        self.desktop.mouse_right_click(modifiers)
        return match

    def double_click(self, image_or_location, modifiers=None):
        """
        Double click over a variety of object types (like hover) using
        the left mouse button and optionally holding special keys
        (like click).
        """
        match = self.hover(image_or_location)
        log.info("Double clicking at %s", image_or_location)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
        self.desktop.mouse_double_click(modifiers)
        return match

    def mouse_down(self, image_or_location, button=LEFT_BUTTON):
        """
        Hold down a mouse button specified by 'button' over a
        variety of object types (like hover).
        """
        match = self.hover(image_or_location)
        log.debug("Holding down the mouse at %s", image_or_location)
        self.desktop.mouse_down(button)
        return match

    def mouse_up(self, image_or_location, button=LEFT_BUTTON):
        """
        Release a mouse button specified by 'button' over a
        variety of object types (like hover).
        """
        match = self.hover(image_or_location)
        log.debug("Holding up the mouse at %s", image_or_location)
        self.desktop.mouse_up(button)
        return match

    def drag_drop(self, src_image_or_location, dst_image_or_location, modifiers=None):
        """
        Drag from and drop at a variety of object types (like hover)
        optionally holding special keys (like click).
        """
        self.drag_from(src_image_or_location, modifiers)
        match = self.drop_at(dst_image_or_location, modifiers)
        return match

    def drag_from(self, image_or_location, modifiers=None):
        """
        Drag from a variety of object types (like hover) optionally
        holding special keys (like click).
        """
        match = self.hover(image_or_location)

        time.sleep(0.2)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
            self.desktop.keys_toggle(modifiers, True)
            #self.desktop.keys_toggle(["Ctrl"], True)

        log.info("Dragging %s", image_or_location)
        self.desktop.mouse_down(self.LEFT_BUTTON)
        time.sleep(Settings.delay_after_drag())

        return match

    def drop_at(self, image_or_location, modifiers=None):
        """
        Drop at a variety of object types (like hover) optionally
        holding special keys (like click).
        """
        match = self.hover(image_or_location)
        time.sleep(Settings.delay_before_drop())

        log.info("Dropping at %s", image_or_location)
        self.desktop.mouse_up(self.LEFT_BUTTON)

        time.sleep(0.5)
        if modifiers != None:
            log.info("Holding the modifiers %s", " ".join(modifiers))
            self.desktop.keys_toggle(modifiers, False)
            #self.desktop.keys_toggle(["Ctrl"], False)

        return match

    def press_keys(self, keys):
        """
        This method types a single key or a list of keys simultaneously.

        Therefore press_keys([Key.ENTER]) is equivalent to press_keys(Key.ENTER).
        Other options are
            press_keys([Key.CTRL, 'X'])
            press_keys(['a', 'b', 3])
        """
        keys_list = self._parse_keys(keys)
        self.desktop.keys_press(keys_list)
        return self

    def press_at(self, keys, image_or_location):
        """
        This method types a single key or a list of keys simultaneously
        at a specified image or location.

        This method is similar to press_keys above.
        """
        keys_list = self._parse_keys(keys, image_or_location)
        match = self.click(image_or_location)
        time.sleep(Settings.delay_before_keys())
        self.desktop.keys_press(keys_list)
        return match

    def _parse_keys(self, keys, image_or_location=None):
        at_str = " at %s" % image_or_location if image_or_location else ""

        keys_list = []
        # if not a list (i.e. if a single key)
        if isinstance(keys, int) or isinstance(keys, basestring):
            key = keys
            try:
                log.info("Pressing key '%s'%s", Key.to_string(key), at_str)
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
                    key_strings.append(Key.to_string(key))
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
        This method specializes in typing a list of consecutive character keys
        (string text without special keys) or a list of strings.

        Therefore type_text(['hello']) is equivalent to type_text('hello').
        Other options are
            type_text('ab3') # compare with press_keys()
            type_text(['Hello', ' ', 'user3614']) # in cases with appending

        Special keys are only allowed as modifiers here, call 'press_keys'
        multiple times for consecutively typing special keys.

        Modifiers is a list equivalent to the one in press_keys().
        """
        text_list = self._parse_text(text)
        if modifiers != None:
            if isinstance(modifiers, basestring):
                modifiers = [modifiers]
            log.info("Holding the modifiers '%s'", "'+'".join(modifiers))
        self.desktop.keys_type(text_list, modifiers)
        return self

    def type_at(self, text, image_or_location, modifiers=None):
        """
        This method specializes in typing a list of consecutive character keys
        (string text without special keys) or a list of strings at a specified
        image or location.

        This method is similar to type_text above.
        """
        text_list = self._parse_text(text, image_or_location)
        match = None
        if image_or_location != None:
            match = self.click(image_or_location)
            time.sleep(Settings.delay_before_keys())
        if modifiers != None:
            if isinstance(modifiers, basestring):
                modifiers = [modifiers]
            log.info("Holding the modifiers '%s'", "'+'".join(modifiers))
        self.desktop.keys_type(text_list, modifiers)
        return match

    def _parse_text(self, text, image_or_location=None):
        at_str = " at %s" % image_or_location if image_or_location else ""

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


# TODO: make this more pythonic
import match
