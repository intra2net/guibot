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
import operator
import autopy.key

# Define keys to current backend key mapping.
# In our case autopy

class Key:
    # commented out keys are not supported by autopy yet
    # this needs to be patched
    ENTER=autopy.key.K_RETURN
    # TAB
    ESC=autopy.key.K_ESCAPE
    BACKSPACE=autopy.key.K_BACKSPACE
    DELETE=autopy.key.K_DELETE
    # INSERT

    CTRL=autopy.key.K_CONTROL
    ALT=autopy.key.K_ALT
    SHIFT=autopy.key.K_SHIFT
    META=autopy.key.K_META

    F1=autopy.key.K_F1
    F2=autopy.key.K_F2
    F3=autopy.key.K_F3
    F4=autopy.key.K_F4
    F5=autopy.key.K_F5
    F6=autopy.key.K_F6
    F7=autopy.key.K_F7
    F8=autopy.key.K_F8
    F9=autopy.key.K_F9
    F10=autopy.key.K_F10
    F11=autopy.key.K_F11
    F12=autopy.key.K_F12

    HOME=autopy.key.K_HOME
    END=autopy.key.K_END
    LEFT=autopy.key.K_LEFT
    RIGHT=autopy.key.K_RIGHT
    UP=autopy.key.K_UP
    DOWN=autopy.key.K_DOWN
    PAGE_DOWN=autopy.key.K_PAGEDOWN
    PAGE_UP=autopy.key.K_PAGEUP

    CAPS_LOCK=autopy.key.K_CAPSLOCK
    # PRINTSCREEN
    # PAUSE
    # SCROLL_LOCK
    # NUM_LOCK

class KeyModifier:
    MOD_NONE=autopy.key.MOD_NONE
    MOD_CTRL=autopy.key.MOD_CONTROL
    MOD_ALT=autopy.key.MOD_ALT
    MOD_SHIFT=autopy.key.MOD_SHIFT
    MOD_META=autopy.key.MOD_META
