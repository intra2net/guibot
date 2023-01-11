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
Simple guibot interface for short scripts, examples, and basic GUI automation.

Frontend with simple procedural API allowing the use of a module instead of
the :py:class:`guibot.GuiBot` object (creating and running this same
object internally). All the methods delegate their calls to this object so
for information about the API please refer to it and :py:class:`region.Region`.


INTERFACE
------------------------------------------------------

"""

from collections import namedtuple

from .guibot import GuiBot


# accessible attributes of this module
guibot = None
last_match = None
buttons = namedtuple('Buttons', ["mouse", "key", "mod"])


def initialize():
    """Initialize the simple API."""
    global guibot
    guibot = GuiBot()
    global last_match
    last_match = guibot.last_match

    global buttons
    buttons.mouse = guibot.dc_backend.mousemap
    buttons.key = guibot.dc_backend.keymap
    buttons.mod = guibot.dc_backend.modmap


def check_initialized():
    """Make sure the simple API is initialized."""
    if guibot is None:
        raise AssertionError("Guibot module not initialized - run initialize() before using the simple API")


def add_path(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    guibot.add_path(*args, **kwargs)


def remove_path(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    guibot.remove_path(*args, **kwargs)


def find(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.find(*args, **kwargs)


def find_all(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.find_all(*args, **kwargs)


def sample(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.sample(*args, **kwargs)


def exists(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.exists(*args, **kwargs)


def wait(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.wait(*args, **kwargs)


def wait_vanish(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.wait_vanish(*args, **kwargs)


def get_mouse_location(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.get_mouse_location(*args, **kwargs)


def idle(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.idle(*args, **kwargs)


def hover(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.hover(*args, **kwargs)


def click(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.click(*args, **kwargs)


def right_click(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.right_click(*args, **kwargs)


def middle_click(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.middle_click(*args, **kwargs)


def double_click(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.double_click(*args, **kwargs)


def multi_click(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.multi_click(*args, **kwargs)


def click_expect(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.click_expect(*args, **kwargs)


def click_vanish(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.click_vanish(*args, **kwargs)


def click_at_index(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.click_at_index(*args, **kwargs)


def mouse_down(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.mouse_down(*args, **kwargs)


def mouse_up(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.mouse_up(*args, **kwargs)


def mouse_scroll(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.mouse_scroll(*args, **kwargs)


def drag_drop(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.drag_drop(*args, **kwargs)


def drag_from(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.drag_from(*args, **kwargs)


def drop_at(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.drop_at(*args, **kwargs)


def press_keys(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.press_keys(*args, **kwargs)


def press_at(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.press_at(*args, **kwargs)


def press_expect(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.press_expect(*args, **kwargs)


def press_vanish(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.press_vanish(*args, **kwargs)


def type_text(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.type_text(*args, **kwargs)


def type_at(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.type_at(*args, **kwargs)


def click_at(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.click_at(*args, **kwargs)


def fill_at(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.fill_at(*args, **kwargs)


def select_at(*args, **kwargs):
    """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
    check_initialized()
    return guibot.select_at(*args, **kwargs)
