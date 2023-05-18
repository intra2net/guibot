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

"""

SUMMARY
------------------------------------------------------
Display controllers (DC backends) to perform user operations.


INTERFACE
------------------------------------------------------

"""

import os
import re
import time
import logging

import PIL.Image
from tempfile import NamedTemporaryFile

from . import inputmap
from .config import GlobalConfig, LocalConfig
from .target import Image
from .location import Location
from .errors import *


log = logging.getLogger('guibot.controller')
__all__ = ['Controller', 'AutoPyController', 'XDoToolController',
           'VNCDoToolController', 'PyAutoGUIController']


class Controller(LocalConfig):
    """
    Screen control backend, responsible for performing desktop operations
    like mouse clicking, key pressing, text typing, etc.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a screen controller backend."""
        super(Controller, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["control"] = "control_methods"
        self.algorithms["control_methods"] = ["autopy", "pyautogui",
                                              "xdotool", "vncdotool"]

        # other attributes
        self._backend_obj = None
        self._width = 0
        self._height = 0
        # NOTE: some backends require mouse pointer reinitialization so compensate for it
        self._pointer = Location(0, 0)
        self._keymap = None
        self._modmap = None
        self._mousemap = None

        # additional preparation
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_width(self):
        """
        Getter for readonly attribute.

        :returns: width of the connected screen
        :rtype: int
        """
        return self._width
    width = property(fget=get_width)

    def get_height(self):
        """
        Getter for readonly attribute.

        :returns: height of the connected screen
        :rtype: int
        """
        return self._height
    height = property(fget=get_height)

    def get_keymap(self):
        """
        Getter for readonly attribute.

        :returns: map of keys to be used for the connected screen
        :rtype: :py:class:`inputmap.Key`
        """
        return self._keymap
    keymap = property(fget=get_keymap)

    def get_mousemap(self):
        """
        Getter for readonly attribute.

        :returns: map of mouse buttons to be used for the connected screen
        :rtype: :py:class:`inputmap.MouseButton`
        """
        return self._mousemap
    mousemap = property(fget=get_mousemap)

    def get_modmap(self):
        """
        Getter for readonly attribute.

        :returns: map of modifier keys to be used for the connected screen
        :rtype: :py:class:`inputmap.KeyModifier`
        """
        return self._modmap
    modmap = property(fget=get_modmap)

    def get_mouse_location(self):
        """
        Getter for readonly attribute.

        :returns: location of the mouse pointer
        :rtype: :py:class:`location.Location`
        """
        return self._pointer
    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(self, backend=None, category="control", reset=False):
        if category != "control":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(Controller, self).configure_backend("dc", reset=True)
        if backend is None:
            backend = GlobalConfig.display_control_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError("Backend '%s' is not among the supported ones: "
                                          "%s" % (backend, self.algorithms[self.categories[category]]))

        log.log(9, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend
        log.log(9, "%s %s\n", category, self.params[category])

    def configure_backend(self, backend=None, category="control", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="control", reset=False):
        if category != "control":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(Controller, self).synchronize_backend("dc", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

    def synchronize_backend(self, backend=None, category="control", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.

        Select a backend for the instance, synchronizing configuration
        like screen size, key map, mouse pointer handling, etc. The
        object that carries this configuration is called screen.
        """
        self.__synchronize_backend(backend, category, reset)

    def _region_from_args(self, *args):
        if len(args) == 4:
            xpos = args[0]
            ypos = args[1]
            width = args[2]
            height = args[3]
        elif len(args) == 1:
            region = args[0]
            xpos = region.x
            ypos = region.y
            width = region.width
            height = region.height
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
        with NamedTemporaryFile(prefix='guibot', suffix='.png') as f:
            # NOTE: the file can be open twice on unix but only once on windows so simply
            # use the generated filename to avoid this difference and remove it manually
            filename = f.name
        return xpos, ypos, width, height, filename

    def capture_screen(self, *args):
        """
        Get the current screen as image.

        :param args: region's (x, y, width, height) or a region object or
                     nothing to obtain an image of the full screen
        :type args: [int] or :py:class:`region.Region` or None
        :returns: image of the current screen
        :rtype: :py:class:`target.Image`
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")

    def mouse_move(self, location, smooth=True):
        """
        Move the mouse to a desired location.

        :param location: location on the screen to move to
        :type location: :py:class:`location.Location`
        :param bool smooth: whether to sue smooth transition or just teleport the mouse
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")

    def mouse_click(self, button=None, count=1, modifiers=None):
        """
        Click the selected mouse button N times at the current mouse location.

        :param button: mouse button, e.g. self.mouse_map.LEFT_BUTTON
        :type button: int or None
        :param int count: number of times to click
        :param modifiers: special keys to hold during clicking
                         (see :py:class:`inputmap.KeyModifier` for extensive list)
        :type modifiers: [str]
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")

    def mouse_down(self, button):
        """
        Hold down a mouse button.

        :param int button: button index depending on backend
                           (see :py:class:`inputmap.MouseButton` for extensive list)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")

    def mouse_up(self, button):
        """
        Release a mouse button.

        :param int button: button index depending on backend
                           (see :py:class:`inputmap.MouseButton` for extensive list)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")

    def mouse_scroll(self, clicks=10, horizontal=False):
        """
        Scroll the mouse for a number of clicks.

        :param int clicks: number of clicks to scroll up (positive) or down (negative)
        :param bool horizontal: whether to perform a horizontal scroll instead
                                (only available on some platforms)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")

    def keys_toggle(self, keys, up_down):
        """
        Hold down or release together all provided keys.

        :param keys: characters or special keys depending on the backend
                     (see :py:class:`inputmap.Key` for extensive list)
        :type keys: [str] or str (no special keys in the second case)
        :param bool up_down: hold down if true else release
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")

    def keys_press(self, keys):
        """
        Press (hold down and release) together all provided keys.

        :param keys: characters or special keys depending on the backend
                     (see :py:class:`inputmap.Key` for extensive list)
        :type keys: [str] or str (no special keys in the second case)
        """
        # BUG: pressing multiple times the same key does not work?
        self.keys_toggle(keys, True)
        self.keys_toggle(keys, False)

    def keys_type(self, text, modifiers=None):
        """
        Type (press consecutively) all provided keys.

        :param text: characters only (no special keys allowed)
        :type text: [str] or str (second case is preferred and first redundant)
        :param modifiers: special keys to hold during typing
                         (see :py:class:`inputmap.KeyModifier` for extensive list)
        :type modifiers: [str]
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError("Method is not available for this controller implementation")


class AutoPyController(Controller):
    """
    Screen control backend implemented through AutoPy which is a small
    python library portable to Windows and Linux operating systems.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a DC backend using AutoPy."""
        super(AutoPyController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_mouse_location(self):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        loc = self._backend_obj.mouse.location()
        # newer versions do their own scale conversion
        version = self._backend_obj.__version__.split(".")
        if int(version[0]) > 3 or int(version[0]) == 3 and (int(version[1]) > 0 or int(version[2]) > 0):
            return Location(int(loc[0] * self._scale), int(loc[1] * self._scale))
        return Location(int(loc[0] / self._scale), int(loc[1] / self._scale))
    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(self, backend=None, category="autopy", reset=False):
        if category != "autopy":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(AutoPyController, self).configure_backend("autopy", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(self, backend=None, category="autopy", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="autopy", reset=False):
        if category != "autopy":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(AutoPyController, self).synchronize_backend("autopy", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

        import autopy
        self._backend_obj = autopy

        self._scale = self._backend_obj.screen.scale()
        self._width, self._height = self._backend_obj.screen.size()
        self._width = int(self._width * self._scale)
        self._height = int(self._height * self._scale)
        self._pointer = self.mouse_location
        self._keymap = inputmap.AutoPyKey()
        self._modmap = inputmap.AutoPyKeyModifier()
        self._mousemap = inputmap.AutoPyMouseButton()

    def synchronize_backend(self, backend=None, category="autopy", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, filename = self._region_from_args(*args)

        # autopy works in points and requires a minimum of one point along a dimension
        xpos, ypos, width, height = xpos / self._scale, ypos / self._scale, width / self._scale, height / self._scale
        xpos, ypos = xpos - (1.0 - width) if width < 1.0 else xpos, ypos - (1.0 - height) if height < 1.0 else ypos
        height, width = 1.0 if height < 1.0 else height, 1.0 if width < 1.0 else width
        try:
            autopy_bmp = self._backend_obj.bitmap.capture_screen(((xpos, ypos), (width, height)))
        except ValueError:
            return Image(None, PIL.Image.new('RGB', (1, 1)))
        autopy_bmp.save(filename)

        with PIL.Image.open(filename) as f:
            pil_image = f.convert('RGB')
        os.unlink(filename)
        return Image(None, pil_image)

    def mouse_move(self, location, smooth=True):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        x, y = location.x / self._scale, location.y / self._scale
        if smooth:
            self._backend_obj.mouse.smooth_move(x, y)
        else:
            self._backend_obj.mouse.move(x, y)
        self._pointer = location

    def mouse_click(self, button=None, count=1, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        toggle_timeout = GlobalConfig.toggle_delay
        click_timeout = GlobalConfig.click_delay
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            self._backend_obj.mouse.click(button)
            # BUG: the mouse button of autopy is pressed down forever (on LEFT)
            time.sleep(toggle_timeout)
            self.mouse_up(button)
            time.sleep(click_timeout)
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouse.toggle(button, True)

    def mouse_up(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouse.toggle(button, False)

    def keys_toggle(self, keys, up_down):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        for key in keys:
            self._backend_obj.key.toggle(key, up_down, [])

    def keys_type(self, text, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

        for part in text:
            for char in str(part):
                self._backend_obj.key.tap(char, [])
                time.sleep(GlobalConfig.delay_between_keys)
            # alternative option:
            # autopy.key.type_string(text)

        if modifiers is not None:
            self.keys_toggle(modifiers, False)


class XDoToolController(Controller):
    """
    Screen control backend implemented through the xdotool client and
    thus portable to Linux operating systems.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a DC backend using XDoTool."""
        super(XDoToolController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_mouse_location(self):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        pos = self._backend_obj.run("getmouselocation")
        x = re.search(r"x:(\d+)", pos).group(1)
        y = re.search(r"y:(\d+)", pos).group(1)
        return Location(int(x), int(y))
    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(self, backend=None, category="xdotool", reset=False):
        if category != "xdotool":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(XDoToolController, self).configure_backend("xdotool", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        self.params[category]["binary"] = "xdotool"

    def configure_backend(self, backend=None, category="xdotool", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="xdotool", reset=False):
        if category != "xdotool":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(XDoToolController, self).synchronize_backend("xdotool", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

        import subprocess
        class XDoTool(object):
            def __init__(self, dc):
                self.dc = dc
            def run(self, command, *args):
                process = [self.dc.params[category]["binary"]]
                process += [command]
                process += args
                return subprocess.check_output(process, shell=False).decode()
        self._backend_obj = XDoTool(self)

        self._width, self._height = self._backend_obj.run("getdisplaygeometry").split()
        self._width, self._height = int(self._width), int(self._height)
        self._pointer = self.mouse_location
        self._keymap = inputmap.XDoToolKey()
        self._modmap = inputmap.XDoToolKeyModifier()
        self._mousemap = inputmap.XDoToolMouseButton()

    def synchronize_backend(self, backend=None, category="xdotool", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, filename = self._region_from_args(*args)
        import subprocess
        with subprocess.Popen(("xwd", "-silent", "-root"), stdout=subprocess.PIPE) as xwd:
            subprocess.call(("convert", "xwd:-", "-crop", "%sx%s+%s+%s" % (width, height, xpos, ypos), filename), stdin=xwd.stdout)
        with PIL.Image.open(filename) as f:
            pil_image = f.convert('RGB')
        os.unlink(filename)
        return Image(None, pil_image)

    def mouse_move(self, location, smooth=True):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if smooth:
            # TODO: implement smooth mouse move?
            log.warning("Smooth mouse move is not supported for the XDO controller,"
                        " defaulting to instant mouse move")
        self._backend_obj.run("mousemove", str(location.x), str(location.y))
        # handle race conditions where the backend coordinates are updated too
        # slowly by giving some time for the new location to take effect there
        time.sleep(0.3)
        self._pointer = location

    def mouse_click(self, button=None, count=1, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        toggle_timeout = GlobalConfig.toggle_delay
        click_timeout = GlobalConfig.click_delay
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            # BUG: the xdotool click is too fast and non-configurable with timeout
            # self._backend_obj.run("click", str(button))
            self.mouse_down(button)
            time.sleep(toggle_timeout)
            self.mouse_up(button)
            time.sleep(click_timeout)
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.run("mousedown", str(button))

    def mouse_up(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.run("mouseup", str(button))

    def keys_toggle(self, keys, up_down):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        for key in keys:
            if up_down:
                self._backend_obj.run('keydown', str(key))
            else:
                self._backend_obj.run('keyup', str(key))

    def keys_type(self, text, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

        for part in text:
            self._backend_obj.run('type', str(part))

        if modifiers is not None:
            self.keys_toggle(modifiers, False)


class VNCDoToolController(Controller):
    """
    Screen control backend implemented through the VNCDoTool client and
    thus portable to any guest OS that is accessible through a VNC/RFB protocol.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a DC backend using VNCDoTool."""
        super(VNCDoToolController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def __configure_backend(self, backend=None, category="vncdotool", reset=False):
        if category != "vncdotool":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(VNCDoToolController, self).configure_backend("vncdotool", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        # hostname of the vnc server
        self.params[category]["vnc_hostname"] = "localhost"
        # port of the vnc server
        self.params[category]["vnc_port"] = 0
        # password for the vnc server
        self.params[category]["vnc_password"] = None

    def configure_backend(self, backend=None, category="vncdotool", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="vncdotool", reset=False):
        if category != "vncdotool":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(VNCDoToolController, self).synchronize_backend("vncdotool", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

        from vncdotool import api
        if self._backend_obj:
            # api.connect() gives us a threaded client, so we need to clean up resources
            # to avoid dangling connections and deadlocks if synchronizing more than once
            self._backend_obj.disconnect()
        self._backend_obj = api.connect('%s:%i' % (self.params[category]["vnc_hostname"],
                                                   self.params[category]["vnc_port"]),
                                        self.params[category]["vnc_password"])
        # for special characters preprocessing for the vncdotool
        self._backend_obj.factory.force_caps = True

        # additional logging for vncdotool available so let's make use of it
        logging.getLogger('vncdotool.client').setLevel(10)
        logging.getLogger('vncdotool').setLevel(logging.ERROR)
        logging.getLogger('twisted').setLevel(logging.ERROR)

        # screen size
        with NamedTemporaryFile(prefix='guibot', suffix='.png') as f:
            filename = f.name
        screen = self._backend_obj.captureScreen(filename)
        os.unlink(filename)
        self._width = screen.width
        self._height = screen.height

        # sync pointer
        self.mouse_move(Location(self._width, self._height), smooth=False)
        self.mouse_move(Location(0, 0), smooth=False)
        self._pointer = Location(0, 0)

        self._keymap = inputmap.VNCDoToolKey()
        self._modmap = inputmap.VNCDoToolKeyModifier()
        self._mousemap = inputmap.VNCDoToolMouseButton()

    def synchronize_backend(self, backend=None, category="vncdotool", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, _ = self._region_from_args(*args)
        self._backend_obj.refreshScreen()
        cropped = self._backend_obj.screen.crop((xpos, ypos, xpos + width, ypos + height))
        pil_image = cropped.convert('RGB')
        return Image(None, pil_image)

    def mouse_move(self, location, smooth=True):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if smooth:
            self._backend_obj.mouseDrag(location.x, location.y, step=30)
        else:
            self._backend_obj.mouseMove(location.x, location.y)
        self._pointer = location

    def mouse_click(self, button=None, count=1, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        toggle_timeout = GlobalConfig.toggle_delay
        click_timeout = GlobalConfig.click_delay
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            # BUG: some VNC servers (as the QEMU built-in) don't handle click events
            # sent too fast, so we sleep between mouse up and down and avoid mousePress
            # self._backend_obj.mousePress(button)
            self.mouse_down(button)
            time.sleep(toggle_timeout)
            self.mouse_up(button)
            time.sleep(click_timeout)
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseDown(button)

    def mouse_up(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseUp(button)

    def keys_toggle(self, keys, up_down):
        """
        Custom implementation of the base method.

        See base method for details.
        """
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

    def keys_type(self, text, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

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
                time.sleep(GlobalConfig.delay_between_keys)
                self._backend_obj.keyPress(char)

        if modifiers is not None:
            self.keys_toggle(modifiers, False)


class PyAutoGUIController(Controller):
    """
    Screen control backend implemented through PyAutoGUI which is a python
    library portable to MacOS, Windows, and Linux operating systems.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a DC backend using PyAutoGUI."""
        super(PyAutoGUIController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_mouse_location(self):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        x, y = self._backend_obj.position()
        return Location(x, y)
    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(self, backend=None, category="pyautogui", reset=False):
        if category != "pyautogui":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(PyAutoGUIController, self).configure_backend("pyautogui", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(self, backend=None, category="pyautogui", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="pyautogui", reset=False):
        if category != "pyautogui":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(PyAutoGUIController, self).synchronize_backend("pyautogui", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

        import pyautogui
        # allow for (0,0) and edge coordinates
        pyautogui.FAILSAFE = False
        self._backend_obj = pyautogui

        self._width, self._height = self._backend_obj.size()
        self._pointer = self.mouse_location
        self._keymap = inputmap.PyAutoGUIKey()
        self._modmap = inputmap.PyAutoGUIKeyModifier()
        self._mousemap = inputmap.PyAutoGUIMouseButton()

    def synchronize_backend(self, backend=None, category="pyautogui", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, _ = self._region_from_args(*args)

        pil_image = self._backend_obj.screenshot(region=(xpos, ypos, width, height))
        return Image(None, pil_image)

    def mouse_move(self, location, smooth=True):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if smooth:
            self._backend_obj.moveTo(location.x, location.y, duration=1)
        else:
            self._backend_obj.moveTo(location.x, location.y)
        self._pointer = location

    def mouse_click(self, button=None, count=1, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        toggle_timeout = GlobalConfig.toggle_delay
        click_timeout = GlobalConfig.click_delay
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            # NOTE: we don't use higher level API calls since we want to also
            # control the toggle speed
            # self._backend_obj.click(clicks=count, interval=click_timeout, button=button)
            self._backend_obj.mouseDown(button=button)
            time.sleep(toggle_timeout)
            self._backend_obj.mouseUp(button=button)
            time.sleep(click_timeout)
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseDown(button=button)

    def mouse_up(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseUp(button=button)

    def mouse_scroll(self, clicks=10, horizontal=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if horizontal:
            self._backend_obj.hscroll(clicks)
        else:
            self._backend_obj.scroll(clicks)

    def keys_toggle(self, keys, up_down):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        for key in keys:
            if up_down:
                self._backend_obj.keyDown(key)
            else:
                self._backend_obj.keyUp(key)

    def keys_type(self, text, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

        for part in text:
            self._backend_obj.typewrite(part, interval=GlobalConfig.delay_between_keys)

        if modifiers is not None:
            self.keys_toggle(modifiers, False)
