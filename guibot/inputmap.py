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


class Key(object):
    """Helper to contain all key mappings for a custom desktop control backend."""

    def __init__(self):
        """Build an instance containing an empty key map."""
        self.ENTER = None
        self.TAB = None
        self.ESC = None
        self.BACKSPACE = None
        self.DELETE = None
        self.INSERT = None

        self.CTRL = None
        self.ALT = None
        self.SHIFT = None
        self.META = None
        self.RCTRL = None
        self.RALT = None
        self.RSHIFT = None
        self.RMETA = None

        self.F1 = None
        self.F2 = None
        self.F3 = None
        self.F4 = None
        self.F5 = None
        self.F6 = None
        self.F7 = None
        self.F8 = None
        self.F9 = None
        self.F10 = None
        self.F11 = None
        self.F12 = None
        self.F13 = None
        self.F14 = None
        self.F15 = None
        self.F16 = None
        self.F17 = None
        self.F18 = None
        self.F19 = None
        self.F20 = None

        self.HOME = None
        self.END = None
        self.LEFT = None
        self.RIGHT = None
        self.UP = None
        self.DOWN = None
        self.PAGE_DOWN = None
        self.PAGE_UP = None

        self.CAPS_LOCK = None
        self.PRINTSCREEN = None
        self.PAUSE = None
        self.SCROLL_LOCK = None
        self.NUM_LOCK = None
        self.SYS_REQ = None
        self.SUPER = None
        self.RSUPER = None
        self.HYPER = None
        self.RHYPER = None
        self.MENU = None

        self.KP0 = None
        self.KP1 = None
        self.KP2 = None
        self.KP3 = None
        self.KP4 = None
        self.KP5 = None
        self.KP6 = None
        self.KP7 = None
        self.KP8 = None
        self.KP9 = None
        self.KP_ENTER = None
        self.KP_DIVIDE = None
        self.KP_MULTIPLY = None
        self.KP_SUBTRACT = None
        self.KP_ADD = None
        self.KP_DECIMAL = None

    def to_string(self, key):
        """
        Provide with a text representation of a desired key
        according to the custom BC backend.

        :param str key: selected key name according to the custom backend
        :returns: text representation of the selected key
        :rtype: str
        :raises: :py:class:`ValueError` if `key` is not found in the current key map
        """
        if key is None:
            raise ValueError("The key %s does not exist in the current key map" % key)
        return {self.ENTER: "Enter",
                self.TAB: "Tab",
                self.ESC: "Esc",
                self.BACKSPACE: "Backspace",
                self.DELETE: "Delete",
                self.INSERT: "Insert",
                self.CTRL: "Ctrl",
                self.ALT: "Alt",
                self.SHIFT: "Shift",
                self.META: "Meta",
                self.RCTRL: "RightControl",
                self.RALT: "RightAlt",
                self.RSHIFT: "RightShift",
                self.RMETA: "RightMeta",
                self.F1: "F1",
                self.F2: "F2",
                self.F3: "F3",
                self.F4: "F4",
                self.F5: "F5",
                self.F6: "F6",
                self.F7: "F7",
                self.F8: "F8",
                self.F9: "F9",
                self.F10: "F10",
                self.F11: "F11",
                self.F12: "F12",
                self.F13: "F13",
                self.F14: "F14",
                self.F15: "F15",
                self.F16: "F16",
                self.F17: "F17",
                self.F18: "F18",
                self.F19: "F19",
                self.F20: "F20",
                self.HOME: "Home",
                self.END: "End",
                self.LEFT: "Left",
                self.RIGHT: "Right",
                self.UP: "Up",
                self.DOWN: "Down",
                self.PAGE_DOWN: "Page Down",
                self.PAGE_UP: "Page Up",
                self.CAPS_LOCK: "Caps Lock",
                self.PRINTSCREEN: "Print Screen",
                self.PAUSE: "Pause",
                self.SCROLL_LOCK: "Scroll Lock",
                self.NUM_LOCK: "Num Lock",
                self.SYS_REQ: "Sys Req",
                self.SUPER: "Super",
                self.RSUPER: "RightSuper",
                self.HYPER: "Hyper",
                self.RHYPER: "RightHyper",
                self.MENU: "Menu"}[key]


class AutoPyKey(Key):
    """Helper to contain all key mappings for the AutoPy DC backend."""

    def __init__(self):
        """Build an instance containing the key map for the AutoPy backend."""
        import autopy
        # commented out keys are not supported by autopy
        # TODO: this needs to be patched
        self.ENTER = autopy.key.K_RETURN
        self.TAB = None
        self.ESC = autopy.key.K_ESCAPE
        self.BACKSPACE = autopy.key.K_BACKSPACE
        self.DELETE = autopy.key.K_DELETE
        self.INSERT = None

        self.CTRL = autopy.key.K_CONTROL
        self.ALT = autopy.key.K_ALT
        self.SHIFT = autopy.key.K_SHIFT
        self.META = autopy.key.K_META
        self.RCTRL = None
        self.RALT = None
        self.RSHIFT = None
        self.RMETA = None

        self.F1 = autopy.key.K_F1
        self.F2 = autopy.key.K_F2
        self.F3 = autopy.key.K_F3
        self.F4 = autopy.key.K_F4
        self.F5 = autopy.key.K_F5
        self.F6 = autopy.key.K_F6
        self.F7 = autopy.key.K_F7
        self.F8 = autopy.key.K_F8
        self.F9 = autopy.key.K_F9
        self.F10 = autopy.key.K_F10
        self.F11 = autopy.key.K_F11
        self.F12 = autopy.key.K_F12
        self.F13 = None
        self.F14 = None
        self.F15 = None
        self.F16 = None
        self.F17 = None
        self.F18 = None
        self.F19 = None
        self.F20 = None

        self.HOME = autopy.key.K_HOME
        self.END = autopy.key.K_END
        self.LEFT = autopy.key.K_LEFT
        self.RIGHT = autopy.key.K_RIGHT
        self.UP = autopy.key.K_UP
        self.DOWN = autopy.key.K_DOWN
        self.PAGE_DOWN = autopy.key.K_PAGEDOWN
        self.PAGE_UP = autopy.key.K_PAGEUP

        self.CAPS_LOCK = autopy.key.K_CAPSLOCK
        self.PRINTSCREEN = None
        self.PAUSE = None
        self.SCROLL_LOCK = None
        self.NUM_LOCK = None
        self.SYS_REQ = None
        self.SUPER = None
        self.RSUPER = None
        self.HYPER = None
        self.RHYPER = None
        self.MENU = None

        self.KP0 = None
        self.KP1 = None
        self.KP2 = None
        self.KP3 = None
        self.KP4 = None
        self.KP5 = None
        self.KP6 = None
        self.KP7 = None
        self.KP8 = None
        self.KP9 = None
        self.KP_ENTER = None
        self.KP_DIVIDE = None
        self.KP_MULTIPLY = None
        self.KP_SUBTRACT = None
        self.KP_ADD = None
        self.KP_DECIMAL = None


class QemuKey(Key):
    """Helper to contain all key mappings for the Qemu DC backend."""

    def __init__(self):
        """Build an instance containing the key map for the Qemu backend."""
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


class VNCDoToolKey(Key):
    """Helper to contain all key mappings for the VNCDoTool DC backend."""

    def __init__(self):
        """Build an instance containing the key map for the VNCDoTool backend."""
        # TODO: it would be preferable to translate directly to RBF like
        # 'ENTER = rfb.KEY_Return' but this is internal for the vncdotool
        self.ENTER = 'return' # also 'enter'
        self.TAB = 'tab'
        self.ESC = 'esc'
        self.BACKSPACE = 'bsp'
        self.DELETE = 'del' # also 'delete'
        self.INSERT = 'ins'

        self.CTRL = 'ctrl' # also 'lctrl'
        self.ALT = 'alt' # also 'lalt'
        self.SHIFT = 'shift' # also 'lshift'
        self.META = 'meta' # also 'lmeta'
        self.RCTRL = 'rctrl'
        self.RALT = 'ralt'
        self.RSHIFT = 'rshift'
        self.RMETA = 'rmeta'

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
        self.F13 = 'f13'
        self.F14 = 'f14'
        self.F15 = 'f15'
        self.F16 = 'f16'
        self.F17 = 'f17'
        self.F18 = 'f18'
        self.F19 = 'f19'
        self.F20 = 'f20'

        self.HOME = 'home'
        self.END = 'end'
        self.LEFT = 'left'
        self.RIGHT = 'right'
        self.UP = 'up'
        self.DOWN = 'down'
        self.PAGE_DOWN = 'pgdn'
        self.PAGE_UP = 'pgup'

        self.CAPS_LOCK = 'caplk'
        # TODO: 'print screen' is not available
        self.PRINTSCREEN = None
        self.PAUSE = 'pause'
        self.SCROLL_LOCK = 'scrlk'
        self.NUM_LOCK = 'numlk'
        self.SYS_REQ = 'sysrq'
        self.SUPER = 'super' # also 'lsuper'
        self.RSUPER = 'rsuper'
        self.HYPER = 'hyper' # also 'lhyper'
        self.RHYPER = 'rhyper'
        # TODO: 'menu' is not available
        self.MENU = None

        self.KP0 = 'kp0'
        self.KP1 = 'kp1'
        self.KP2 = 'kp2'
        self.KP3 = 'kp3'
        self.KP4 = 'kp4'
        self.KP5 = 'kp5'
        self.KP6 = 'kp6'
        self.KP7 = 'kp7'
        self.KP8 = 'kp8'
        self.KP9 = 'kp9'
        self.KP_ENTER = 'kpenter'
        # TODO: these are not available
        self.KP_DIVIDE = None
        self.KP_MULTIPLY = None
        self.KP_SUBTRACT = None
        self.KP_ADD = None
        self.KP_DECIMAL = None


class KeyModifier(object):
    """Helper to contain all modifier key mappings for a custom desktop control backend."""

    def __init__(self):
        """Build an instance containing an empty modifier key map."""
        self.MOD_NONE = None
        self.MOD_CTRL = None
        self.MOD_ALT = None
        self.MOD_SHIFT = None
        self.MOD_META = None

    def to_string(self, key):
        """
        Provide with a text representation of a desired modifier key
        according to the custom BC backend.

        :param str key: selected modifier name according to the current backend
        :returns: text representation of the selected modifier
        :rtype: str
        :raises: :py:class:`ValueError` if `key` is not found in the current modifier map
        """
        if key is None:
            raise ValueError("The modifier key %s does not exist in the current modifier map" % key)
        return {self.MOD_NONE: "None",
                self.MOD_CTRL: "Ctrl",
                self.MOD_ALT: "Alt",
                self.MOD_SHIFT: "Shift",
                self.MOD_META: "Meta"}[key]


class AutoPyKeyModifier(KeyModifier):
    """Helper to contain all modifier key mappings for the AutoPy DC backend."""

    def __init__(self):
        """Build an instance containing the modifier key map for the AutoPy backend."""
        import autopy
        self.MOD_NONE = autopy.key.MOD_NONE
        self.MOD_CTRL = autopy.key.MOD_CONTROL
        self.MOD_ALT = autopy.key.MOD_ALT
        self.MOD_SHIFT = autopy.key.MOD_SHIFT
        self.MOD_META = autopy.key.MOD_META


class QemuKeyModifier(KeyModifier):
    """Helper to contain all modifier key mappings for the Qemu DC backend."""

    def __init__(self):
        """Build an instance containing the modifier key map for the Qemu backend."""
        # TODO: 'none' is not available
        self.MOD_NONE = None
        self.MOD_CTRL = 'ctrl'
        self.MOD_ALT = 'alt'
        self.MOD_SHIFT = 'shift'
        # TODO: 'meta' is not available
        self.MOD_META = None


class VNCDoToolKeyModifier(KeyModifier):
    """Helper to contain all modifier key mappings for the VNCDoTool DC backend."""

    def __init__(self):
        """Build an instance containing the modifier key map for the VNCDoTool backend."""
        # TODO: 'none' is not available
        self.MOD_NONE = None
        self.MOD_CTRL = 'ctrl'
        self.MOD_ALT = 'alt'
        self.MOD_SHIFT = 'shift'
        self.MOD_META = 'meta'


class MouseButton(object):
    """Helper to contain all mouse button mappings for a custom desktop control backend."""

    def __init__(self):
        """Build an instance containing an empty mouse button map."""
        self.LEFT_BUTTON = None
        self.RIGHT_BUTTON = None
        self.CENTER_BUTTON = None

    def to_string(self, key):
        """
        Provide with a text representation of a desired mouse button
        according to the custom BC backend.

        :param str key: selected mouse button according to the current backend
        :returns: text representation of the selected mouse button
        :rtype: str
        :raises: :py:class:`ValueError` if `key` is not found in the current mouse map
        """
        if key is None:
            raise ValueError("The key %s does not exist in the current mouse map" % key)
        return {self.LEFT_BUTTON: "MouseLeft",
                self.RIGHT_BUTTON: "MouseRight",
                self.CENTER_BUTTON: "MouseCenter"}[key]


class AutoPyMouseButton(MouseButton):
    """Helper to contain all mouse button mappings for the AutoPy DC backend."""

    def __init__(self):
        """Build an instance containing the mouse button map for the AutoPy backend."""
        import autopy
        self.LEFT_BUTTON = autopy.mouse.LEFT_BUTTON
        self.RIGHT_BUTTON = autopy.mouse.RIGHT_BUTTON
        self.CENTER_BUTTON = autopy.mouse.CENTER_BUTTON


class QemuMouseButton(MouseButton):
    """Helper to contain all mouse button mappings for the Qemu DC backend."""

    def __init__(self):
        """Build an instance containing the mouse button map for the Qemu backend."""
        self.LEFT_BUTTON = 1
        self.RIGHT_BUTTON = 4
        self.CENTER_BUTTON = 2


class VNCDoToolMouseButton(MouseButton):
    """Helper to contain all mouse button mappings for the VNCDoTool DC backend."""

    def __init__(self):
        """Build an instance containing the mouse button map for the VNCDoTool backend."""
        self.LEFT_BUTTON = 1
        self.RIGHT_BUTTON = 3
        self.CENTER_BUTTON = 2

