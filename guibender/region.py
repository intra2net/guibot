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
import logging
import time, sys

# interconnected classes - import only their modules
# to avoid circular reference
from desktopcontrol import DesktopControl

from errors import *
from location import Location
from image import Image
from imagefinder import ImageFinder

class Region(object):
    # Mouse buttons
    LEFT_BUTTON=DesktopControl.LEFT_BUTTON
    RIGHT_BUTTON=DesktopControl.RIGHT_BUTTON
    CENTER_BUTTON=DesktopControl.CENTER_BUTTON

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
            self.xpos = screen_width -1

        if self.ypos > screen_height:
            self.ypos = screen_height -1

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

    def nearby(self, range=50):
        new_xpos = self.xpos - range
        if new_xpos < 0:
            new_xpos = 0

        new_ypos = self.ypos - range
        if new_ypos < 0:
            new_ypos = 0

        new_width = self.width + range + self.xpos - new_xpos
        new_height = self.height + range + self.ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, new_ypos, new_width, new_height)

    def above(self, range=0):
        if range == 0:
            new_ypos = 0
            new_height = self.ypos + self.height
        else:
            new_ypos = self.ypos - range
            if new_ypos < 0:
                new_ypos = 0

            new_height = self.height + self.ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(self.xpos, new_ypos, self.width, new_height)

    def below(self, range=0):
        if range == 0:
            range = self.desktop.get_height()

        new_height = self.height + range

        # Final clipping is done in the Region constructor
        return Region(self.xpos, self.ypos, self.width, new_height)

    def left(self, range=0):
        if range == 0:
            new_xpos = 0
            new_width = self.xpos + self.width
        else:
            new_xpos = self.xpos - range
            if new_xpos < 0:
                new_xpos = 0

            new_width = self.width + self.xpos - new_xpos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, self.ypos, new_width, self.height)

    def right(self, range=0):
        if range == 0:
            range = self.desktop.get_width()

        new_width = self.width + range

        # Final clipping is done in the Region constructor
        return Region(self.xpos, self.ypos, new_width, self.height)

    def get_last_match(self):
        return self.last_match

    def find(self, image, timeout=10):
        # Load image if needed
        if isinstance(image, basestring):
            image = Image(image)

        timeout_limit = time.time() + timeout
        while True:
            screen_capture = self.desktop.capture_screen(self)
            similarity = image.get_similarity()

            found_pic = self.imagefinder.find_image(screen_capture, image, similarity, 0, 0, self.width, self.height)
            if found_pic is not None:
                self.last_match = match.Match(self.xpos + found_pic.get_x(), self.ypos + found_pic.get_y(), image)
                return self.last_match

            if time.time() > timeout_limit:
                # TODO: Turn this into a setting / make it optional
                screen_capture.save('/tmp/guibender_last_finderror.png')
                image.save('/tmp/guibender_last_finderror_needle.png')

                break

            # don't hog the CPU
            # TODO: Make 'rescan speed' configurable
            time.sleep(0.2)

        raise FindError()

    def exists(self, image, timeout=0):
        try:
            return self.find(image, timeout)
        except:
            pass

        return None

    def wait(self, image, timeout=30):
        return self.find(image, timeout)

    def wait_vanish(self, image, timeout=30):
        expires = time.time() + timeout
        while time.time() < expires:
            if self.exists(image, 0) is None:
                return True

            # don't hog the CPU
            time.sleep(0.2)

        # image is still there
        return False

    def get_mouse_location(self):
        return self.desktop.get_mouse_location()

    def hover(self, image_or_location):
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

    def click(self, image_or_location, modifiers = None):
        match = self.hover(image_or_location)
        self.desktop.mouse_click(modifiers)
        return match

    def right_click(self, image_or_location, modifiers = None):
        match = self.hover(image_or_location)
        self.desktop.mouse_right_click(modifiers)
        return match

    def double_click(self, image_or_location, modifiers = None):
        match = self.hover(image_or_location)
        self.desktop.mouse_double_click(modifiers)
        return match

    def mouse_down(self, image_or_location, button=LEFT_BUTTON):
        match = self.hover(image_or_location)
        self.desktop.mouse_down(button)
        return match

    def mouse_up(self, image_or_location, button=LEFT_BUTTON):
        match = self.hover(image_or_location)
        self.desktop.mouse_up(button)
        return match

    def drag_drop(self, src_image_or_location, dst_image_or_location, modifiers = None):
        self.drag(src_image_or_location, modifiers)
        match = self.drop_at(dst_image_or_location, modifiers)
        return match

    def drag(self, image_or_location, modifiers = None):
        match = self.hover(image_or_location)

        time.sleep(0.2)
        self.desktop.keys_toggle(modifiers, True)
        #self.desktop.keys_toggle(["Ctrl"], True)

        self.desktop.mouse_down(self.LEFT_BUTTON)
        # TODO: Make delay after drag configurable
        time.sleep(0.5)

        return match

    def drop_at(self, image_or_location, modifiers = None):
        match = self.hover(image_or_location)

        # TODO: Make delay before drop configurable
        time.sleep(0.5)

        self.desktop.mouse_up(self.LEFT_BUTTON)

        time.sleep(0.5)
        self.desktop.keys_toggle(modifiers, False)
        #self.desktop.keys_toggle(["Ctrl"], False)

        return match

    # Press key combinations - text must be a list
    # of special characters
    def press(self, keys):
        self.desktop.keys_press(keys)
        return self

    def press_at(self, image_or_location=None, keys=[]):
        match = None
        if image_or_location != None:
            match = self.click(image_or_location)
            # TODO: Make configurable
            time.sleep(0.2)

        self.desktop.keys_press(keys)
        return match

    def type_text(self, text, modifiers=None):
        self.desktop.keys_type(text, modifiers)
        return self

    def type_at(self, image_or_location=None, text='', modifiers=None):
        match = None
        if image_or_location != None:
            match = self.click(image_or_location)
            # TODO: Make configurable
            time.sleep(0.2)

        self.desktop.keys_type(text, modifiers)
        return match

    # List of API functions to implement:
    #
    # find_all(Image or filename)

# TODO: make this more pythonic
import match
