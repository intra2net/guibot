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

BACKEND = Settings.desktop_control_backend()
if BACKEND in ["autopy-win", "autopy-nix"]:
    import autopy.screen
    import autopy.mouse
    import autopy.key
    if BACKEND == "autopy-nix":
        import subprocess
elif BACKEND == "qemu":
    monitor = None # TODO: set externally?
elif BACKEND == "vncdotool":
    from vncdotool import api
    client = api.connect('%s:%i' % (Settings.vnc_hostname(), Settings.vnc_port()))
# NOTE: some backends require mouse pointer reinitialization so compensate for it
POINTER = Location(0, 0)

class DesktopControl:

    def __init__(self):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            screen_size = autopy.screen.get_size()
            self.width = screen_size[0]
            self.height = screen_size[1]
        elif BACKEND == "qemu":
            if not monitor:
                raise ValueError("No Qemu monitor was selected - please set a monitor object first.")
            with NamedTemporaryFile(prefix='guibender', suffix='.ppm') as f:
                filename = f.name
            monitor.screendump(filename=filename, debug=True)
            screen = PIL.Image.open(filename)
            os.unlink(filename)
            self.width = screen.size[0]
            self.height = screen.size[1]
        elif BACKEND == "vncdotool":
            # TODO: try to avoid the file performance slowdown
            with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
                filename = f.name
            screen = client.captureScreen(filename)
            os.unlink(filename)
            self.width = screen.width
            self.height = screen.height

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

        # TODO: Switch to in-memory conversion - patch backends or request get_raw() from authors
        with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
            # NOTE: the file can be open twice on unix but only once on windows so simply
            # use the generated filename to avoid this difference and remove it manually
            filename = f.name

        if BACKEND in ["autopy-win", "autopy-nix"]:

            # BUG: autopy screen capture on Windows must use negative coordinates,
            # but it doesn't and as a result any normal attempt to capture a subregion
            # will fall outside of the screen (be black) - it also blocks us trying to
            # use negative coordinates screaming that we are outside of the screen while
            # thinking that the coordinates are positive - this was already registered
            # as a bug on autopy's GitHub page but no progress has been made since that
            # -> https://github.com/msanders/autopy/issues/32
            autopy_bmp = autopy.bitmap.capture_screen(((xpos, ypos), (width, height)))
            autopy_bmp.save(filename)

            pil_image = PIL.Image.open(filename).convert('RGB')
        elif BACKEND == "qemu":
            # TODO: capture subregion own implementation?
            monitor.screendump(filename=filename, debug=True)
            pil_image = PIL.Image.open(filename)
        elif BACKEND == "vncdotool":
            client.captureRegion(filename, xpos, ypos, width, height)
            pil_image = PIL.Image.open(filename).convert('RGB')
        os.unlink(filename)
        return Image(None, pil_image)

    def get_mouse_location(self):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            pos = autopy.mouse.get_pos()
            return Location(pos[0], pos[1])
        else:
            return POINTER

    def mouse_move(self, location, smooth=True):
        # NOTE: we need this to be able to set the variable
        global POINTER
        if BACKEND in ["autopy-win", "autopy-nix"]:
            # TODO: sometimes this is not pixel perfect, i.e.
            # need to investigate the autopy source later on
            if smooth:
                autopy.mouse.smooth_move(location.get_x(), location.get_y())
            else:
                autopy.mouse.move(location.get_x(), location.get_y())
        elif BACKEND == "qemu":
            if smooth:
                # TODO: implement smooth mouse move?
                pass
            monitor.mouse_move(location.get_x(), location.get_y())
            POINTER = location
        elif BACKEND == "vncdotool":
            if smooth:
                client.mouseDrag(location.get_x(), location.get_y(), step=30)
            else:
                client.mouseMove(location.get_x(), location.get_y())
            POINTER = location

    def mouse_click(self, modifiers=None):
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        if BACKEND in ["autopy-win", "autopy-nix"]:
            autopy.mouse.click(MouseButton.LEFT_BUTTON)
        elif BACKEND == "qemu":
            monitor.mouse_button(MouseButton.LEFT_BUTTON)
        elif BACKEND == "vncdotool":
            client.mousePress(MouseButton.LEFT_BUTTON)
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_right_click(self, modifiers=None):
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        if BACKEND in ["autopy-win", "autopy-nix"]:
            autopy.mouse.click(MouseButton.RIGHT_BUTTON)
        elif BACKEND == "qemu":
            monitor.mouse_button(MouseButton.RIGHT_BUTTON)
        elif BACKEND == "vncdotool":
            client.mousePress(MouseButton.RIGHT_BUTTON)
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_double_click(self, modifiers=None):
        timeout = Settings.click_delay()
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        if BACKEND in ["autopy-win", "autopy-nix"]:
            autopy.mouse.click(MouseButton.LEFT_BUTTON)
            time.sleep(timeout)
            autopy.mouse.click(MouseButton.LEFT_BUTTON)
        elif BACKEND == "qemu":
            monitor.mouse_button(MouseButton.LEFT_BUTTON)
            time.sleep(timeout)
            monitor.mouse_button(MouseButton.LEFT_BUTTON)
        elif BACKEND == "vncdotool":
            client.mousePress(MouseButton.LEFT_BUTTON)
            time.sleep(timeout)
            client.mousePress(MouseButton.LEFT_BUTTON)
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button=MouseButton.LEFT_BUTTON):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            autopy.mouse.toggle(True, button)
        elif BACKEND == "qemu":
            # TODO: sync with autopy button
            monitor.mouse_button(button)
        elif BACKEND == "vncdotool":
            # TODO: sync with autopy button
            client.mouseDown(button)

    def mouse_up(self, button=MouseButton.LEFT_BUTTON):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            autopy.mouse.toggle(False, button)
        elif BACKEND == "qemu":
            # TODO: sync with autopy button
            monitor.mouse_button(button)
        elif BACKEND == "vncdotool":
            # TODO: sync with autopy button
            client.mouseUp(button)

    def keys_toggle(self, keys, up_down):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            for key in keys:
                autopy.key.toggle(key, up_down)
        elif BACKEND == "qemu":
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
            monitor.sendkey("-".join(keys), hold_time=1)
        elif BACKEND == "vncdotool":
            for key in keys:
                if key == "\\":
                    key = 'bslash'
                elif key == "/":
                    key = 'fslash'
                elif key == " ":
                    key = 'space'
                if up_down:
                    client.keyDown(key)
                else:
                    client.keyUp(key)

    def keys_press(self, keys):
        self.keys_toggle(keys, True)
        self.keys_toggle(keys, False)

    def keys_type(self, text, modifiers):
        if modifiers != None:
            self.keys_toggle(modifiers, True)

        if BACKEND == "autopy-win":
            shift_chars = ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
                           "_", "+", "{", "}", ":", "\"", "|", "<", ">", "?"]
            capital_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for part in text:
                for char in str(part):
                    if char in shift_chars:
                        autopy.key.tap(char, KeyModifier.MOD_SHIFT)
                    elif char in capital_chars:
                        autopy.key.tap(char, KeyModifier.MOD_SHIFT)
                    else:
                        autopy.key.tap(char)
                # TODO: Fix autopy to handle international chars and other stuff so
                # that both the Linux and Windows version are reduced to autopy.key
                # autopy.key.type_string(text)
        elif BACKEND == "autopy-nix":
            for part in text:
                # HACK: use xdotool to handle various character encoding
                subprocess.call(['xdotool', 'type', part], shell=False)
        elif BACKEND == "qemu":
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
            for part in text:
                for char in str(part):
                    if qemu_escape_map.has_key(char):
                        char = qemu_escape_map[char]
                    monitor.sendkey(char, hold_time=1)
        elif BACKEND == "vncdotool":
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
                    client.keyPress(char)

        if modifiers != None:
            self.keys_toggle(modifiers, False)
