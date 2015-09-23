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

import PIL.Image
from tempfile import NamedTemporaryFile

from settings import Settings
from image import Image
from location import Location
from inputmap import KeyModifier, MouseButton


class DesktopControl:

    def __init__(self):
        self._backend_name = None
        self._backend_obj = None
        self._width = None
        self._height = None
        # NOTE: some backends require mouse pointer reinitialization so compensate for it
        self._pointer = Location(0, 0)

        self._backend_name = Settings.desktop_control_backend()
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            # dependencies
            import autopy.screen
            import autopy.mouse
            if self._backend_name == "autopy-nix":
                import subprocess
            else:
                import autopy.key
            # object
            self._backend_obj = autopy
            # screen size
            screen_size = self._backend_obj.screen.get_size()
            self._width = screen_size[0]
            self._height = screen_size[1]
        elif self._backend_name == "qemu":
            # object
            self._backend_obj = Settings.qemu_monitor()
            if not self._backend_obj:
                raise ValueError("No Qemu monitor was selected - please set a monitor object first.")
            # screen size
            with NamedTemporaryFile(prefix='guibender', suffix='.ppm') as f:
                filename = f.name
            self._backend_obj.screendump(filename=filename, debug=True)
            screen = PIL.Image.open(filename)
            os.unlink(filename)
            self._width = screen.size[0]
            self._height = screen.size[1]
        elif self._backend_name == "vncdotool":
            # imports
            from vncdotool import api
            import logging
            logging.getLogger('vncdotool').setLevel(logging.ERROR)
            logging.getLogger('twisted').setLevel(logging.ERROR)
            # object
            self._backend_obj = api.connect('%s:%i' % (Settings.vnc_hostname(), Settings.vnc_port()))
            if Settings.preprocess_special_chars():
                self._backend_obj.factory.force_caps = True
            # screen size
            with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
                filename = f.name
            screen = self._backend_obj.captureScreen(filename)
            os.unlink(filename)
            self._width = screen.width
            self._height = screen.height

    def get_backend(self):
        return self._backend_name

    def get_width(self):
        return self._width

    def get_height(self):
        return self._height

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
            width = self._width
            height = self._height

        # clipping
        if xpos > self._width:
            xpos = self._width - 1
        if ypos > self._height:
            ypos = self._height - 1
        if xpos + width > self._width:
            width = self._width - xpos
        if ypos + height > self._height:
            height = self._height - ypos

        # TODO: Switch to in-memory conversion - patch backends or request get_raw() from authors
        with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
            # NOTE: the file can be open twice on unix but only once on windows so simply
            # use the generated filename to avoid this difference and remove it manually
            filename = f.name

        if self._backend_name in ["autopy-win", "autopy-nix"]:

            # BUG: autopy screen capture on Windows must use negative coordinates,
            # but it doesn't and as a result any normal attempt to capture a subregion
            # will fall outside of the screen (be black) - it also blocks us trying to
            # use negative coordinates screaming that we are outside of the screen while
            # thinking that the coordinates are positive - this was already registered
            # as a bug on autopy's GitHub page but no progress has been made since that
            # -> https://github.com/msanders/autopy/issues/32
            autopy_bmp = self._backend_obj.bitmap.capture_screen(((xpos, ypos), (width, height)))
            autopy_bmp.save(filename)

            pil_image = PIL.Image.open(filename).convert('RGB')
        elif self._backend_name == "qemu":
            # TODO: capture subregion own implementation?
            self._backend_obj.screendump(filename=filename, debug=True)
            pil_image = PIL.Image.open(filename)
        elif self._backend_name == "vncdotool":
            self._backend_obj.captureRegion(filename, xpos, ypos, width, height)
            pil_image = PIL.Image.open(filename).convert('RGB')
        os.unlink(filename)
        return Image(None, pil_image)

    def get_mouse_location(self):
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            pos = self._backend_obj.mouse.get_pos()
            return Location(pos[0], pos[1])
        else:
            return self._pointer

    def mouse_move(self, location, smooth=True):
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            # TODO: sometimes this is not pixel perfect, i.e.
            # need to investigate the autopy source later on
            if smooth:
                self._backend_obj.mouse.smooth_move(location.get_x(), location.get_y())
            else:
                self._backend_obj.mouse.move(location.get_x(), location.get_y())
        elif self._backend_name == "qemu":
            if smooth:
                # TODO: implement smooth mouse move?
                pass
            self._backend_obj.mouse_move(location.get_x(), location.get_y())
            self._pointer = location
        elif self._backend_name == "vncdotool":
            if smooth:
                self._backend_obj.mouseDrag(location.get_x(), location.get_y(), step=30)
            else:
                self._backend_obj.mouseMove(location.get_x(), location.get_y())
            self._pointer = location

    def mouse_click(self, modifiers=None):
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            self._backend_obj.mouse.click(MouseButton.LEFT_BUTTON)
        elif self._backend_name == "qemu":
            # BUG: the mouse_button monitor command resets the mouse position to
            # (0,0) making it impossible to click anywhere else, see this for more info:
            # http://lists.nongnu.org/archive/html/qemu-devel/2013-06/msg02506.html
            self._backend_obj.mouse_button(MouseButton.LEFT_BUTTON)
        elif self._backend_name == "vncdotool":
            self._backend_obj.mousePress(MouseButton.LEFT_BUTTON)
            # BUG: the mouse button is pressed down forever (on LEFT)
            self._backend_obj.mouseUp(MouseButton.LEFT_BUTTON)
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_right_click(self, modifiers=None):
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            self._backend_obj.mouse.click(MouseButton.RIGHT_BUTTON)
        elif self._backend_name == "qemu":
            self._backend_obj.mouse_button(MouseButton.RIGHT_BUTTON)
        elif self._backend_name == "vncdotool":
            self._backend_obj.mousePress(MouseButton.RIGHT_BUTTON)
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_double_click(self, modifiers=None):
        timeout = Settings.click_delay()
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            self._backend_obj.mouse.click(MouseButton.LEFT_BUTTON)
            time.sleep(timeout)
            self._backend_obj.mouse.click(MouseButton.LEFT_BUTTON)
        elif self._backend_name == "qemu":
            self._backend_obj.mouse_button(MouseButton.LEFT_BUTTON)
            time.sleep(timeout)
            self._backend_obj.mouse_button(MouseButton.LEFT_BUTTON)
        elif self._backend_name == "vncdotool":
            self._backend_obj.mousePress(MouseButton.LEFT_BUTTON)
            # BUG: the mouse button is pressed down forever (on LEFT)
            self._backend_obj.mouseUp(MouseButton.LEFT_BUTTON)
            time.sleep(timeout)
            self._backend_obj.mousePress(MouseButton.LEFT_BUTTON)
            # BUG: the mouse button is pressed down forever (on LEFT)
            self._backend_obj.mouseUp(MouseButton.LEFT_BUTTON)
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button=MouseButton.LEFT_BUTTON):
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            self._backend_obj.mouse.toggle(True, button)
        elif self._backend_name == "qemu":
            # TODO: sync with autopy button
            self._backend_obj.mouse_button(button)
        elif self._backend_name == "vncdotool":
            # TODO: sync with autopy button
            self._backend_obj.mouseDown(button)

    def mouse_up(self, button=MouseButton.LEFT_BUTTON):
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            self._backend_obj.mouse.toggle(False, button)
        elif self._backend_name == "qemu":
            # TODO: sync with autopy button
            self._backend_obj.mouse_button(button)
        elif self._backend_name == "vncdotool":
            # TODO: sync with autopy button
            self._backend_obj.mouseUp(button)

    def keys_toggle(self, keys, up_down):
        if self._backend_name in ["autopy-win", "autopy-nix"]:
            for key in keys:
                self._backend_obj.key.toggle(key, up_down)
        elif self._backend_name == "qemu":
            qemu_escape_map = {"\\": '0x2b',
                               "/" : 'slash',
                               " " : 'spc',
                               "*" : 'asterisk',
                               "-" : 'minus',
                               "=" : 'equal',
                               "," : 'comma',
                               "." : 'dot',
                               ";" : '0x27',
                               "'" : '0x28',
                               "`" : '0x29',
                               # TODO: verify '<' (since autotest != qemu doc)
                               "<" : '0x2b',
                               "(" : '0x1a',
                               ")" : '0x1b'
                               }
            for key in keys:
                if qemu_escape_map.has_key(key):
                    key = qemu_escape_map[key]
            # TODO: test and handle longer hold
            self._backend_obj.sendkey("-".join(keys), hold_time=1)
        elif self._backend_name == "vncdotool":
            for key in keys:
                if key == "\\":
                    key = 'bslash'
                elif key == "/":
                    key = 'fslash'
                elif key == " ":
                    key = 'space'
                if up_down:
                    self._backend_obj.keyDown(key)
                else:
                    self._backend_obj.keyUp(key)

    def keys_press(self, keys):
        self.keys_toggle(keys, True)
        self.keys_toggle(keys, False)

    def keys_type(self, text, modifiers):
        if modifiers != None:
            self.keys_toggle(modifiers, True)

        if self._backend_name == "autopy-win":
            shift_chars = ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
                           "_", "+", "{", "}", ":", "\"", "|", "<", ">", "?"]
            capital_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for part in text:
                for char in str(part):
                    if char in shift_chars and Settings.preprocess_special_chars():
                        self._backend_obj.key.tap(char, KeyModifier.MOD_SHIFT)
                    elif char in capital_chars and Settings.preprocess_special_chars():
                        self._backend_obj.key.tap(char, KeyModifier.MOD_SHIFT)
                    else:
                        self._backend_obj.key.tap(char)
                # TODO: Fix autopy to handle international chars and other stuff so
                # that both the Linux and Windows version are reduced to autopy.key
                # autopy.key.type_string(text)
        elif self._backend_name == "autopy-nix":
            for part in text:
                # HACK: use xdotool to handle various character encoding
                subprocess.call(['xdotool', 'type', part], shell=False)
        elif self._backend_name == "qemu":
            special_chars = {"~": "`", "!": "1", "@": "2", "#": "3", "$": "4",
                             "%": "5", "^": "6", "&": "7", "*": "8", "(": "9",
                             ")": "0", "_": "-", "+": "=", "{": "[", "}": "]",
                             ":": ";", "\"": "'", "|":  "\\", "<": ",", ">": ".", "?": "/"}
            capital_chars = {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F":"f", "G": "g",
                             "H": "h", "I": "i", "J": "j", "K": "k", "L": "l", "M": "m", "N": "n",
                             "O": "o", "P": "p", "Q": "q", "R": "r", "S": "s", "T": "t", "U": "u",
                             "V": "v", "W": "w", "X": "x", "Y": "y", "Z": "z"}
            qemu_escape_map = {"\\": '0x2b',
                               "/" : 'slash',
                               " " : 'spc',
                               "*" : 'asterisk',
                               "-" : 'minus',
                               "=" : 'equal',
                               "," : 'comma',
                               "." : 'dot',
                               ";" : '0x27',
                               "'" : '0x28',
                               "`" : '0x29',
                               "<" : '0x2b',
                               "(" : '0x1a',
                               ")" : '0x1b'
                               }
            # TODO: the following characters still have problems ~()_+[]{}:\"|<>?
            for part in text:
                for char in str(part):
                    if qemu_escape_map.has_key(char):
                        char = qemu_escape_map[char]
                    elif capital_chars.has_key(char) and Settings.preprocess_special_chars():
                        char = "shift-%s" % capital_chars[char]
                    elif special_chars.has_key(char) and Settings.preprocess_special_chars():
                        char = "shift-%s" % special_chars[char]
                    self._backend_obj.sendkey(char, hold_time=1)
        elif self._backend_name == "vncdotool":
            for part in text:
                for char in str(part):
                    if char == "\\":
                        char = 'bslash'
                    elif char == "/":
                        char = 'fslash'
                    elif char == " ":
                        char = 'space'
                    elif char == "\n":
                        char = 'return'
                    self._backend_obj.keyPress(char)

        if modifiers != None:
            self.keys_toggle(modifiers, False)
