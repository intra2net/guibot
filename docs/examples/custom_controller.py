#!/usr/bin/python3

# Only needed if not installed system wide
import sys
sys.path.insert(0, '../..')


# Program start here
#
# Experimental custom controller to implement interaction with Qemu virtual
# machines. This is a partial illustration of how to create custom controller.
#
# TODO: This example is still unfinished, we have to restore the full usability
# of these instances first.

import os
import time
import PIL
from tempfile import NamedTemporaryFile

from guibot.controller import Controller
from guibot.errors import *
from guibot.inputmap import Key, KeyModifier, MouseButton
from guibot.config import GlobalConfig
from guibot.target import Image
from guibot.location import Location


class QemuKey(Key):
    """Helper to contain all key mappings for the Qemu DC backend."""

    def __init__(self):
        """Build an instance containing the key map for the Qemu backend."""
        super().__init__()

        self.ENTER = 'ret'
        self.TAB = 'tab'
        self.ESC = 'esc'
        self.BACKSPACE = 'backspace'
        self.DELETE = 'delete'
        self.INSERT = 'insert'

        self.CTRL = 'ctrl'
        self.ALT = 'alt'
        # TODO: if needed these are also supported
        # altgr, altgr_r (right altgr)
        self.SHIFT = 'shift'
        # TODO: 'meta' is not available
        self.META = None
        self.RCTRL = 'ctrl_r'
        self.RALT = 'alt_r'
        self.RSHIFT = 'shift_r'
        # TODO: 'right meta' is not available
        self.RMETA = None

        self.F1 = 'f1'
        self.F2 = 'f2'
        self.F3 = 'f3'
        self.F4 = 'f4'
        self.F5 = 'f5'
        self.F6 = 'f6'
        self.F7 = 'f7'
        self.F8 = 'f8'
        self.F9 = 'f9'
        self.F10 = 'f10'
        self.F11 = 'f11'
        self.F12 = 'f12'
        # TODO: these function keys are not available
        self.F13 = None
        self.F14 = None
        self.F15 = None
        self.F16 = None
        self.F17 = None
        self.F18 = None
        self.F19 = None
        self.F20 = None

        self.HOME = 'home'
        self.END = 'end'
        self.LEFT = 'left'
        self.RIGHT = 'right'
        self.UP = 'up'
        self.DOWN = 'down'
        self.PAGE_DOWN = 'pgdn'
        self.PAGE_UP = 'pgup'

        self.CAPS_LOCK = 'caps_lock'
        self.PRINTSCREEN = 'print'
        # TODO: 'pause' is not available
        self.PAUSE = None
        self.SCROLL_LOCK = 'scroll_lock'
        self.NUM_LOCK = 'num_lock'
        self.SYS_REQ = 'sysrq'
        self.SUPER = '0xdc'
        self.RSUPER = '0xdb'
        # TODO: 'hyper' and 'right hyper' are not available
        self.HYPER = None
        self.RHYPER = None
        self.MENU = "menu"

        self.KP0 = 'kp_0'
        self.KP1 = 'kp_1'
        self.KP2 = 'kp_2'
        self.KP3 = 'kp_3'
        self.KP4 = 'kp_4'
        self.KP5 = 'kp_5'
        self.KP6 = 'kp_6'
        self.KP7 = 'kp_7'
        self.KP8 = 'kp_8'
        self.KP9 = 'kp_9'
        self.KP_ENTER = 'kp_enter'
        self.KP_DIVIDE = 'kp_divide'
        self.KP_MULTIPLY = 'kp_multiply'
        self.KP_SUBTRACT = 'kp_subtract'
        self.KP_ADD = 'kp_add'
        self.KP_DECIMAL = 'kp_decimal'


class QemuKeyModifier(KeyModifier):
    """Helper to contain all modifier key mappings for the Qemu DC backend."""

    def __init__(self):
        """Build an instance containing the modifier key map for the Qemu backend."""
        super().__init__()

        # TODO: 'none' is not available
        self.MOD_NONE = None
        self.MOD_CTRL = 'ctrl'
        self.MOD_ALT = 'alt'
        self.MOD_SHIFT = 'shift'
        # TODO: 'meta' is not available
        self.MOD_META = None


class QemuMouseButton(MouseButton):
    """Helper to contain all mouse button mappings for the Qemu DC backend."""

    def __init__(self):
        """Build an instance containing the mouse button map for the Qemu backend."""
        super().__init__()

        self.LEFT_BUTTON = 1
        self.RIGHT_BUTTON = 4
        self.CENTER_BUTTON = 2


class QemuController(Controller):
    """
    Screen control backend implemented through the Qemu emulator and
    thus portable to any guest OS that runs on virtual machine.

    .. note:: This backend can be used in accord with a qemu monitor
              object (python) provided by a library like virt-test.
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a DC backend using Qemu."""
        super(QemuController, self).__init__(configure=False, synchronize=False)
        self.algorithms["control_methods"] += ["qemu"]
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def __configure_backend(self, backend=None, category="qemu", reset=False):
        if category != "qemu":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(QemuController, self).configure_backend("qemu", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        # qemu monitor object in case qemu backend is used
        self.params[category]["qemu_monitor"] = None

    def configure_backend(self, backend=None, category="qemu", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(self, backend=None, category="qemu", reset=False):
        if category != "qemu":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(QemuController, self).synchronize_backend("qemu", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError("Backend '%s' has not been configured yet" % backend)

        self._backend_obj = self.params[category]["qemu_monitor"]
        if self._backend_obj is None:
            raise ValueError("No Qemu monitor was selected - please set a monitor object first.")

        # screen size
        with NamedTemporaryFile(prefix='guibot', suffix='.ppm') as f:
            filename = f.name
        self._backend_obj.screendump(filename=filename, debug=True)
        # use context manager here and everywhere else, then also use image.flush()
        with PIL.Image.open(filename) as screen:
            os.unlink(filename)
            self._width, self._height = screen.size

        # sync pointer
        self.mouse_move(Location(self._width, self._height), smooth=False)
        self.mouse_move(Location(0, 0), smooth=False)
        self._pointer = Location(0, 0)

        self._keymap = QemuKey()
        self._modmap = QemuKeyModifier()
        self._mousemap = QemuMouseButton()

    def synchronize_backend(self, backend=None, category="qemu", reset=False):
        """
        Custom implementation of the base method.

        :raises: :py:class:`ValueError` if control backend is 'qemu' and no monitor is selected

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, filename = self._region_from_args(*args)
        # TODO: capture subregion not present - own implementation?
        self._backend_obj.screendump(filename=filename, debug=True)
        with PIL.Image.open(filename) as pil_image:
            os.unlink(filename)
            screendump = Image(None, pil_image)
        return screendump

    def mouse_move(self, location, smooth=True):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        if smooth:
            # TODO: implement smooth mouse move?
            pass
        self._backend_obj.mouse_move(location.x, location.y)
        self._pointer = location

    def mouse_click(self, button=None, count=1, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers != None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            self._backend_obj.mouse_button(button)
            # BUG: QEMU's monitor doesn't handle click events sent too fast,
            # so we sleep a bit between mouse up and mouse down
            time.sleep(self.params["control"]["mouse_toggle_delay"])
            self._backend_obj.mouse_button(button)
            time.sleep(self.params["control"]["after_click_delay"])
        if modifiers != None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouse_button(button)

    def mouse_up(self, button):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        # TODO: need mouse up handling
        self._backend_obj.mouse_button(button)

    def keys_toggle(self, keys, up_down):
        """
        Custom implementation of the base method.

        See base method for details.
        """
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
        espaced_keys = []
        for key in keys:
            espaced_keys += [qemu_escape_map[key] if qemu_escape_map.has_key(key) else key]
        # TODO: test and handle longer hold
        self._backend_obj.sendkey("-".join(espaced_keys), hold_time=1)

    def keys_type(self, text, modifiers=None):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        time.sleep(self.params["control"]["delay_before_keys"])
        if modifiers != None:
            self.keys_toggle(modifiers, True)

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
                elif capital_chars.has_key(char) and GlobalConfig.preprocess_special_chars:
                    char = "shift-%s" % capital_chars[char]
                elif special_chars.has_key(char) and GlobalConfig.preprocess_special_chars:
                    char = "shift-%s" % special_chars[char]
                self._backend_obj.sendkey(char, hold_time=1)
                time.sleep(self.params["control"]["delay_between_keys"])

        if modifiers != None:
            self.keys_toggle(modifiers, False)
