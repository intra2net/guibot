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

from settings import Settings

BACKEND = Settings.desktop_control_backend()
if BACKEND in ["autopy-win", "autopy-nix"]:
    import autopy.key
elif BACKEND == "qemu":
    monitor = None # TODO: set externally?
elif BACKEND == "vncdotool":
    from vncdotool import api
    # TODO: host and display!
    client = api.connect('vnchost:display')


# TODO: Define the key maps for the other two backends
# Define keys to current backend key mapping.


class Key:

    if BACKEND in ["autopy-win", "autopy-nix"]:
        # commented out keys are not supported by autopy
        # TODO: this needs to be patched

        ENTER = autopy.key.K_RETURN
        TAB = None
        ESC = autopy.key.K_ESCAPE
        BACKSPACE = autopy.key.K_BACKSPACE
        DELETE = autopy.key.K_DELETE
        INSERT = None

        CTRL = autopy.key.K_CONTROL
        ALT = autopy.key.K_ALT
        SHIFT = autopy.key.K_SHIFT
        META = autopy.key.K_META
        RCTRL = None
        RALT = None
        RSHIFT = None
        RMETA = None

        F1 = autopy.key.K_F1
        F2 = autopy.key.K_F2
        F3 = autopy.key.K_F3
        F4 = autopy.key.K_F4
        F5 = autopy.key.K_F5
        F6 = autopy.key.K_F6
        F7 = autopy.key.K_F7
        F8 = autopy.key.K_F8
        F9 = autopy.key.K_F9
        F10 = autopy.key.K_F10
        F11 = autopy.key.K_F11
        F12 = autopy.key.K_F12
        F13 = None
        F14 = None
        F15 = None
        F16 = None
        F17 = None
        F18 = None
        F19 = None
        F20 = None

        HOME = autopy.key.K_HOME
        END = autopy.key.K_END
        LEFT = autopy.key.K_LEFT
        RIGHT = autopy.key.K_RIGHT
        UP = autopy.key.K_UP
        DOWN = autopy.key.K_DOWN
        PAGE_DOWN = autopy.key.K_PAGEDOWN
        PAGE_UP = autopy.key.K_PAGEUP

        CAPS_LOCK = autopy.key.K_CAPSLOCK
        PRINTSCREEN = None
        PAUSE = None
        SCROLL_LOCK = None
        NUM_LOCK = None
        SYS_REQ = None
        SUPER = None
        RSUPER = None
        HYPER = None
        RHYPER = None
        MENU = None

        KP0 = None
        KP1 = None
        KP2 = None
        KP3 = None
        KP4 = None
        KP5 = None
        KP6 = None
        KP7 = None
        KP8 = None
        KP9 = None
        KP_ENTER = None
        KP_DIVIDE = None
        KP_MULTIPLY = None
        KP_SUBTRACT = None
        KP_ADD = None
        KP_DECIMAL = None

    elif BACKEND == "qemu":

        ENTER = 'ret'
        TAB = 'tab'
        ESC = 'esc'
        BACKSPACE = 'backspace'
        DELETE = 'delete'
        INSERT = 'insert'
        # TODO: check for parsing issues and/or move to the typing wrappers
        BSLASH = '0x2b'
        FSLASH = 'slash'
        SPACE = 'spc'
        MINUS = "minus"
        EQUAL = "equal"
        COMMA = "comma"
        PERIOD = "dot"
        SEMICOLON = "0x27"
        APOSTROPHE = "0x28"
        GRAVE = "0x29"
        LESS = "0x2b"
        BRACKETLEFT = "0x1a"
        BRACKETRIGHT = "0x1b"

        CTRL = 'ctrl'
        ALT = 'alt'
        # TODO: if needed these are also supported
        # altgr, altgr_r (right altgr)
        SHIFT = 'shift'
        # TODO: 'meta' is not available
        META = None
        RCTRL = 'ctrl_r'
        RALT = 'alt_r'
        RSHIFT = 'shift_r'
        # TODO: 'right meta' is not available
        RMETA = None

        F1 = 'f1'
        F2 = 'f2'
        F3 = 'f3'
        F4 = 'f4'
        F5 = 'f5'
        F6 = 'f6'
        F7 = 'f7'
        F8 = 'f8'
        F9 = 'f9'
        F10 = 'f10'
        F11 = 'f11'
        F12 = 'f12'
        # TODO: these function keys are not available
        F13 = None
        F14 = None
        F15 = None
        F16 = None
        F17 = None
        F18 = None
        F19 = None
        F20 = None

        HOME = 'home'
        END = 'end'
        LEFT = 'left'
        RIGHT = 'right'
        UP = 'up'
        DOWN = 'down'
        PAGE_DOWN = 'pgdn'
        PAGE_UP = 'pgup'

        CAPS_LOCK = 'caps_lock'
        PRINTSCREEN = 'print'
        # TODO: 'pause' is not available
        PAUSE = None
        SCROLL_LOCK = 'scroll_lock'
        NUM_LOCK = 'num_lock'
        SYS_REQ = 'sysrq'
        SUPER = '0xdc'
        RSUPER = '0xdb'
        # TODO: 'hyper' and 'right hyper' are not available
        HYPER = None
        RHYPER = None
        MENU = "menu"

        KP0 = 'kp_0'
        KP1 = 'kp_1'
        KP2 = 'kp_2'
        KP3 = 'kp_3'
        KP4 = 'kp_4'
        KP5 = 'kp_5'
        KP6 = 'kp_6'
        KP7 = 'kp_7'
        KP8 = 'kp_8'
        KP9 = 'kp_9'
        KP_ENTER = 'kp_enter'
        KP_DIVIDE = 'kp_divide'
        KP_MULTIPLY = 'kp_multiply'
        KP_SUBTRACT = 'kp_subtract'
        KP_ADD = 'kp_add'
        KP_DECIMAL = 'kp_decimal'

    elif BACKEND == "vncdotool":

        # TODO: it would be preferable to translate directly to RBF like
        # 'ENTER = rfb.KEY_Return' but this is internal for the vncdotool
        ENTER = 'return' # also 'enter'
        TAB = 'tab'
        ESC = 'esc'
        BACKSPACE = 'bsp'
        DELETE = 'del' # also 'delete'
        INSERT = 'ins'
        # TODO: check for parsing issues and/or move to the typing wrappers
        BSLASH = 'bslash' # also 'slash'
        FSLASH = 'fslash'
        SPACE = 'space' # also 'spacebar', 'sb'

        CTRL = 'ctrl' # also 'lctrl'
        ALT = 'alt' # also 'lalt'
        SHIFT = 'shift' # also 'lshift'
        META = 'meta' # also 'lmeta'
        RCTRL = 'rctrl'
        RALT = 'ralt'
        RSHIFT = 'rshift'
        RMETA = 'rmeta'

        F1 = 'f1'
        F2 = 'f2'
        F3 = 'f3'
        F4 = 'f4'
        F5 = 'f5'
        F6 = 'f6'
        F7 = 'f7'
        F8 = 'f8'
        F9 = 'f9'
        F10 = 'f10'
        F11 = 'f11'
        F12 = 'f12'
        F13 = 'f13'
        F14 = 'f14'
        F15 = 'f15'
        F16 = 'f16'
        F17 = 'f17'
        F18 = 'f18'
        F19 = 'f19'
        F20 = 'f20'

        HOME = 'home'
        END = 'end'
        LEFT = 'left'
        RIGHT = 'right'
        UP = 'up'
        DOWN = 'down'
        PAGE_DOWN = 'pgdn'
        PAGE_UP = 'pgup'

        CAPS_LOCK = 'caplk'
        # TODO: 'print screen' is not available
        PRINTSCREEN = None
        PAUSE = 'pause'
        SCROLL_LOCK = 'scrlk'
        NUM_LOCK = 'numlk'
        SYS_REQ = 'sysrq'
        SUPER = 'super' # also 'lsuper'
        RSUPER = 'rsuper'
        HYPER = 'hyper' # also 'lhyper'
        RHYPER = 'rhyper'
        # TODO: 'menu' is not available
        MENU = None

        KP0 = 'kp0'
        KP1 = 'kp1'
        KP2 = 'kp2'
        KP3 = 'kp3'
        KP4 = 'kp4'
        KP5 = 'kp5'
        KP6 = 'kp6'
        KP7 = 'kp7'
        KP8 = 'kp8'
        KP9 = 'kp9'
        KP_ENTER = 'kpenter'
        # TODO: these are not available
        KP_DIVIDE = None
        KP_MULTIPLY = None
        KP_SUBTRACT = None
        KP_ADD = None
        KP_DECIMAL = None

    @staticmethod
    def to_string(key):
        return {Key.ENTER: "Enter",
                Key.TAB: "Tab",
                Key.ESC: "Esc",
                Key.BACKSPACE: "Backspace",
                Key.DELETE: "Delete",
                Key.INSERT: "Insert",
                Key.CTRL: "Ctrl",
                Key.ALT: "Alt",
                Key.SHIFT: "Shift",
                Key.META: "Meta",
                Key.RCTRL: "RightControl",
                Key.RALT: "RightAlt",
                Key.RSHIFT: "RightShift",
                Key.RMETA: "RightMeta",
                Key.F1: "F1",
                Key.F2: "F2",
                Key.F3: "F3",
                Key.F4: "F4",
                Key.F5: "F5",
                Key.F6: "F6",
                Key.F7: "F7",
                Key.F8: "F8",
                Key.F9: "F9",
                Key.F10: "F10",
                Key.F11: "F11",
                Key.F12: "F12",
                Key.F13: "F13",
                Key.F14: "F14",
                Key.F15: "F15",
                Key.F16: "F16",
                Key.F17: "F17",
                Key.F18: "F18",
                Key.F19: "F19",
                Key.F20: "F20",
                Key.HOME: "Home",
                Key.END: "End",
                Key.LEFT: "Left",
                Key.RIGHT: "Right",
                Key.UP: "Up",
                Key.DOWN: "Down",
                Key.PAGE_DOWN: "Page Down",
                Key.PAGE_UP: "Page Up",
                Key.CAPS_LOCK: "Caps Lock",
                Key.PRINTSCREEN: "Print Screen",
                Key.PAUSE: "Pause",
                Key.SCROLL_LOCK: "Scroll Lock",
                Key.NUM_LOCK: "Num Lock",
                Key.SYS_REQ: "Sys Req",
                Key.SUPER: "Super",
                Key.RSUPER: "RightSuper",
                Key.HYPER: "Hyper",
                Key.RHYPER: "RightHyper",
                Key.MENU: "Menu"}[key]


class KeyModifier:

    if BACKEND in ["autopy-win", "autopy-nix"]:
        MOD_NONE = autopy.key.MOD_NONE
        MOD_CTRL = autopy.key.MOD_CONTROL
        MOD_ALT = autopy.key.MOD_ALT
        MOD_SHIFT = autopy.key.MOD_SHIFT
        MOD_META = autopy.key.MOD_META
    elif BACKEND == "qemu":
        raise NotImplementedError
    elif BACKEND == "vncdotool":
        raise NotImplementedError

    @staticmethod
    def to_string(key):
        return {KeyModifier.MOD_NONE: "None",
                KeyModifier.MOD_CTRL: "Ctrl",
                KeyModifier.MOD_ALT: "Alt",
                KeyModifier.MOD_SHIFT: "Shift",
                KeyModifier.MOD_META: "Meta"}[key]

class MouseButton:

    if BACKEND in ["autopy-win", "autopy-nix"]:
        LEFT_BUTTON = autopy.mouse.LEFT_BUTTON
        RIGHT_BUTTON = autopy.mouse.RIGHT_BUTTON
        CENTER_BUTTON = autopy.mouse.CENTER_BUTTON
    elif BACKEND == "qemu":
        # TODO: check if 1=left, 2=middle, 4=right as described in the scarce documentation
        LEFT_BUTTON = 0
        RIGHT_BUTTON = 2
        CENTER_BUTTON = 4
    elif BACKEND == "vncdotool":
        # TODO: check if 1=left, 2=middle, 4=right or 3=right?
        LEFT_BUTTON = 1
        RIGHT_BUTTON = 2
        CENTER_BUTTON = 3

    @staticmethod
    def to_string(key):
        return {MouseButton.LEFT_BUTTON: "MouseLeft",
                MouseButton.RIGHT_BUTTON: "MouseRight",
                MouseButton.CENTER_BUTTON: "MouseCenter"}[key]
