#!/usr/bin/python
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
# guibender simple, procedural API.
# Creates an internal GuiBender() object.

import os, sys

from guibender import GuiBender

guibender = GuiBender()

LEFT_BUTTON=GuiBender.LEFT_BUTTON
RIGHT_BUTTON=GuiBender.RIGHT_BUTTON
CENTER_BUTTON=GuiBender.CENTER_BUTTON

# return main guibender object
def get_guibender():
    return guibender

def add_image_path(directory):
    guibender.add_image_path(directory)

def remove_image_path(directory):
    guibender.remove_image_path(directory)

def find(image, timeout=10):
    return guibender.find(image, timeout)

def exists(image, timeout=0):
    return guibender.exists(image, timeout)

def wait(image, timeout=30):
    return guibender.wait(image, timeout)

def wait_vanish(image, timeout=30):
    return guibender.wait_vanish(image, timeout)

def get_mouse_location(self):
    return guibender.get_mouse_location()

def hover(image_or_location):
    return guibender.hover(image_or_location)

def click(image_or_location, modifiers = None):
    return guibender.click(image_or_location, modifiers)

def right_click(image_or_location, modifiers = None):
    return guibender.right_click(image_or_location, modifiers)

def double_click(image_or_location, modifiers = None):
    return guibender.double_click(image_or_location, modifiers)

def mouse_down(image_or_location, button=LEFT_BUTTON):
    return guibender.mouse_down(image_or_location, button)

def mouse_up(image_or_location, button=LEFT_BUTTON):
    return guibender.mouse_up(image_or_location, button)

def drag_drop(src_image_or_location, dst_image_or_location, modifiers = None):
    return guibender.drag_drop(src_image_or_location, dst_image_or_location, modifiers)

def drag(image_or_location, modifiers = None):
    return guibender.drag(image_or_location, modifiers)

def drop_at(image_or_location, modifiers = None):
    return guibender.drop_at(image_or_location, modifiers)

def press(keys, duration=0):
    return guibender.press(keys, duration)

def press_at(image_or_location=None, keys=[], duration=0):
    return guibender.press_at(image_or_location, keys, duration)

def type_text(text, modifiers=None):
    return guibender.type_text(text, modifiers)

def type_at(image_or_location=None, text='', modifiers=None):
    return guibender.type_at(image_or_location, text, modifiers)
