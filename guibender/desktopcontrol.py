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
    # TODO: host and display!
    client = api.connect('vnchost:display')

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

        if BACKEND in ["autopy-win", "autopy-nix"]:
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
        elif BACKEND == "qemu":
            # TODO: capture subregion?
            return monitor.screendump('screenshot.png')
        elif BACKEND == "vncdotool":
            return client.captureRegion(xpos, ypos, width, height)

    def mouse_move(self, location, smooth=True):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            # TODO: sometimes this is not pixel perfect, i.e.
            # need to investigate the autopy source later on
            if smooth:
                autopy.mouse.smooth_move(location.get_x(), location.get_y())
            else:
                autopy.mouse.move(location.get_x(), location.get_y())
        elif BACKEND == "qemu":
            if smooth:
                # TODO: does such thing exist?
                raise NotImplementedError
            else:
                # TODO: test since this might be (dx,dy) instead of (x,y)
                monitor.mouse_move(location.get_x(), location.get_y())
        elif BACKEND == "vncdotool":
            if smooth:
                client.mouseDrag(location.get_x(), location.get_y(), step=30)
            else:
                client.mouseMove(location.get_x(), location.get_y())

    def get_mouse_location(self):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            pos = autopy.mouse.get_pos()
        elif BACKEND == "qemu":
            # TODO: figure this out
            raise NotImplementedError
        elif BACKEND == "vncdotool":
            # TODO: figure this out
            raise NotImplementedError
        return Location(pos[0], pos[1])

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

    def key_toggle(self, key, up_down):
        if BACKEND in ["autopy-win", "autopy-nix"]:
            autopy.key.toggle(keys, up_down)
        elif BACKEND == "qemu":
            # TODO: test and handle longer hold
            monitor.sendkey(key, hold_time=1)
        elif BACKEND == "vncdotool":
            if up_down:
                client.keyUp(key)
            else:
                client.keyDown(key)

    def keys_toggle(self, keys, up_down):
        try:
            # Support lists
            for key in keys:
                self.key_toggle(key, up_down)
        except:
            self.key_toggle(key, up_down)

    def keys_press(self, keys):
        self.keys_toggle(keys, True)
        self.keys_toggle(keys, False)

    def keys_type(self, text, modifiers):
        if modifiers != None:
            self.keys_toggle(modifiers, True)

        if isinstance(text, basestring) or isinstance(text, str):
            self._type_string_wrapper(text)
            return

        # Support list of something
        for subtext in text:
            if isinstance(subtext, basestring) or isinstance(subtext, str):
                self._type_string_wrapper(subtext)
            else:
                autopy.key.tap(subtext)

        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def _type_string_wrapper(self, text):
        # TODO: Fix autopy to handle international chars and other stuff so
        # that both the Linux and Windows version are reduced to autopy.key
        if BACKEND == "autopy-win":
            for char in str(text):
                if char in ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+",
                            "{", "}", ":", "\"", "|", "<", ">", "?"]:
                    autopy.key.tap(char, KeyModifier.MOD_SHIFT)
                elif char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    autopy.key.tap(char, KeyModifier.MOD_SHIFT)
                else:
                    autopy.key.tap(char)
            # autopy.key.type_string(text)
        elif BACKEND == "autopy-nix":
            # HACK: use xdotool to handle various character encoding
            subprocess.call(['xdotool', 'type', text], shell=False)
        elif BACKEND == "qemu":
            for char in str(text):
                monitor.sendkey(char, hold_time=1)
        elif BACKEND == "vncdotool":
            for char in str(text):
                client.keyPress(char)
            # TODO: try client.type(text)
