#!/usr/bin/python
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
Frontend with simple procedural API allowing the use of a module instead of
the :py:class:`guibot.GuiBot` object (creating and running this same
object internally). All the methods delegate their calls to this object so
for information about the API please refer to it and :py:class:`region.Region`.
"""

from guibot import GuiBot

# accessible attributes of this module
guibot = GuiBot()
last_match = guibot.last_match


def add_path(directory):
    guibot.add_path(directory)


def remove_path(directory):
    guibot.remove_path(directory)


def find(target, timeout=10):
    return guibot.find(target, timeout)


def find_all(target, timeout=10, allow_zero=False):
    return guibot.find_all(target, timeout, allow_zero)


def sample(target):
    return guibot.sample(target)


def exists(target, timeout=0):
    return guibot.exists(target, timeout)


def wait(target, timeout=30):
    return guibot.wait(target, timeout)


def wait_vanish(target, timeout=30):
    return guibot.wait_vanish(target, timeout)


def get_mouse_location():
    return guibot.get_mouse_location()


def hover(target_or_location):
    return guibot.hover(target_or_location)


def click(target_or_location, modifiers=None):
    return guibot.click(target_or_location, modifiers)


def right_click(target_or_location, modifiers=None):
    return guibot.right_click(target_or_location, modifiers)


def double_click(target_or_location, modifiers=None):
    return guibot.double_click(target_or_location, modifiers)


def multi_click(target_or_location, count=3, modifiers=None):
    return guibot.multi_click(target_or_location, count, modifiers)


def click_expect(click_image_or_location, expect_image_or_location=None, modifiers=None, timeout=60):
    return guibot.click_expect(click_image_or_location, expect_image_or_location, modifiers, timeout)


def click_vanish(click_image_or_location, expect_image_or_location=None, modifiers=None, timeout=60):
    return guibot.click_vanish(click_image_or_location, expect_image_or_location, modifiers, timeout)


def click_at_index(anchor, index=0, find_number=3, timeout=10):
    return guibot.click_at_index(anchor, index, find_number, timeout)


def mouse_down(target_or_location, button=None):
    return guibot.mouse_down(target_or_location, button)


def mouse_up(target_or_location, button=None):
    return guibot.mouse_up(target_or_location, button)


def drag_drop(src_target_or_location, dst_target_or_location, modifiers=None):
    return guibot.drag_drop(src_target_or_location, dst_target_or_location, modifiers)


def drag_from(target_or_location, modifiers=None):
    return guibot.drag(target_or_location, modifiers)


def drop_at(target_or_location, modifiers=None):
    return guibot.drop_at(target_or_location, modifiers)


def press_keys(keys):
    return guibot.press(keys)


def press_at(target_or_location=None, keys=None):
    return guibot.press_at(target_or_location, keys)


def type_text(text, modifiers=None):
    return guibot.type_text(text, modifiers)


def type_at(target_or_location=None, text='', modifiers=None):
    return guibot.type_at(target_or_location, text, modifiers)


def fill_at(anchor, text, dx, dy, del_flag=True, esc_flag=True, mark_click="double"):
    return guibot.fill_at(anchor, text, dx, dy, del_flag, esc_flag, mark_click)


def select_at(anchor, image_or_index, dx, dy, dw=0, dh=0):
    return guibot.select_at(anchor, image_or_index, dx, dy, dw, dh)
