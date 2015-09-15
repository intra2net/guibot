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
import os
import time

import autopy.screen
import autopy.mouse
import autopy.key

import PIL.Image
from tempfile import NamedTemporaryFile

from image import Image
from location import Location
from key import KeyModifier
from settings import Settings

import subprocess

# TODO: implement more backends!

class DesktopControl:
    # Mouse buttons
    LEFT_BUTTON = autopy.mouse.LEFT_BUTTON
    RIGHT_BUTTON = autopy.mouse.RIGHT_BUTTON
    CENTER_BUTTON = autopy.mouse.CENTER_BUTTON

    def __init__(self):
        screen_size = autopy.screen.get_size()

        self.width = screen_size[0]
        self.height = screen_size[1]

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def capture_screen(self, *args):
        if len(args) == 4:
            xpos = args[0]
            ypos = args[1]
            width = args[2]
            height = args[3]
        elif len(args) == 1:
            region = args[0]
            xpos = region.get_x()
            ypos = region.get_y()
            width = region.get_width()
            height = region.get_height()
        else:
            xpos = 0
            ypos = 0
            width = self.width
            height = self.height

        # clipping
        if xpos > self.width:
            xpos = self.width - 1
        if ypos > self.height:
            ypos = self.height - 1

        if xpos + width > self.width:
            width = self.width - xpos
        if ypos + height > self.height:
            height = self.height - ypos

        # TODO: Switch to in-memory conversion. toString()
        # is a base64 encoded, zlib compressed stream.
        # Ask autopy author about a get_raw() method.
        with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
            # the file can be open twice on unix but only once on windows so close
            # it to avoid this difference (and remove it manually afterwards)
            f.close()

            # BUG: autopy screen capture on Windows must use negative coordinates,
            # but it doesn't and as a result any normal attempt to capture a subregion
            # will fall outside of the screen (be black) - it also blocks us trying to
            # use negative coordinates screaming that we are outside of the screen while
            # thinking that the coordinates are positive - this was already registered
            # as a bug on autopy's GitHub page but no progress has been made since that
            # -> https://github.com/msanders/autopy/issues/32
            autopy_bmp = autopy.bitmap.capture_screen(((xpos, ypos), (width, height)))
            autopy_bmp.save(f.name)

            pil_image = PIL.Image.open(f.name).convert('RGB')
            os.unlink(f.name)
            return Image(None, pil_image)

    def mouse_move(self, location):
        # Note: Sometimes this is not pixel perfect.
        # Need to investigate the autopy source later on
        autopy.mouse.smooth_move(location.get_x(), location.get_y())

    def get_mouse_location(self):
        autopy_pos = autopy.mouse.get_pos()
        return Location(autopy_pos[0], autopy_pos[1])

    def mouse_click(self, modifiers=None):
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        autopy.mouse.click()
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_right_click(self, modifiers=None):
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        autopy.mouse.click(autopy.mouse.RIGHT_BUTTON)
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_double_click(self, modifiers=None):
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        autopy.mouse.click()
        # TODO: Make double click speed configurable
        time.sleep(0.1)
        autopy.mouse.click()
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button=LEFT_BUTTON):
        autopy.mouse.toggle(True, button)

    def mouse_up(self, button=LEFT_BUTTON):
        autopy.mouse.toggle(False, button)

    def keys_toggle(self, keys, up_down):
        try:
            # Support lists
            for key in keys:
                autopy.key.toggle(key, up_down)
        except:
            autopy.key.toggle(keys, up_down)

    def keys_press(self, keys):
        self.keys_toggle(keys, True)
        self.keys_toggle(keys, False)

    def keys_type(self, text, modifiers):
        if modifiers != None:
            self.keys_toggle(modifiers, True)

        if isinstance(text, basestring) or isinstance(text, str):
            self._autopy_type_string_wrapper(text)
            return

        # Support list of something
        for subtext in text:
            if isinstance(subtext, basestring) or isinstance(subtext, str):
                self._autopy_type_string_wrapper(subtext)
            else:
                autopy.key.tap(subtext)

        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def _autopy_type_string_wrapper(self, text):
        # TODO: Fix autopy to handle international chars and other stuff so
        # that both the Linux and Windows version are reduced to autopy.key
        if Settings.os_name() in ["Windows", "windows"]:
            for char in str(text):
                if char in ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+",
                            "{", "}", ":", "\"", "|", "<", ">", "?"]:
                    autopy.key.tap(char, KeyModifier.MOD_SHIFT)
                elif char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    autopy.key.tap(char, KeyModifier.MOD_SHIFT)
                else:
                    autopy.key.tap(char)
            # autopy.key.type_string(text)
        elif Settings.os_name() in ["Linux", "linux"]:
            subprocess.call(['xdotool', 'type', text], shell=False)
        else:
            raise ValueError("Unrecognized operating system - must be one of 'windows', 'linux'.")
