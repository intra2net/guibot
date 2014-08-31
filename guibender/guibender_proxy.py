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
#
# Use Pyro4 proxifying GuiBender object (serialize-compatible API),
# creating the GuiBender object locally.

import os, sys

from guibender import GuiBender


class GuiBenderProxy(GuiBender):
    """
    The proxy guibender object is just a wrapper around the actual guibender
    object that takes care of returning easily serializable Pyro4 proxy objects
    instead of the real ones or their serialized copies.

    It allows you to move the mouse, type text and do any other GuiBender action
    from code which is executed on another machine somewhere on the network.
    """

    def __init__(self):
        super(GuiBenderProxy, self).__init__()

    def _proxify(self, obj):
        if isinstance(obj, (int, float, bool, basestring)) or obj is None:
            return obj
        if obj not in self._pyroDaemon.objectsById.values():
            self._pyroDaemon.register(obj)
        return obj

    def last_match(self):
        return self._proxify(super(GuiBender, self).get_last_match())

    def find(self, image, timeout=10):
        return self._proxify(super(GuiBender, self).find(image, timeout))

    def find_all(self, image, timeout=10, allow_zero=False):
        return self._proxify(super(GuiBender, self).find_all(image, timeout, allow_zero))

    def sample(self, image):
        return self._proxify(super(GuiBender, self).sample(image))

    def exists(self, image, timeout=0):
        return self._proxify(super(GuiBender, self).exists(image, timeout))

    def wait(self, image, timeout=30):
        return self._proxify(super(GuiBender, self).wait(image, timeout))

    def wait_vanish(self, image, timeout=30):
        return self._proxify(super(GuiBender, self).wait_vanish(image, timeout))

    def get_mouse_location(self):
        return self._proxify(super(GuiBender, self).get_mouse_location())

    def hover(self, image_or_location):
        return self._proxify(super(GuiBender, self).hover(image_or_location))

    def click(self, image_or_location, modifiers = None):
        return self._proxify(super(GuiBender, self).click(image_or_location, modifiers))

    def right_click(self, image_or_location, modifiers = None):
        return self._proxify(super(GuiBender, self).right_click(image_or_location, modifiers))

    def double_click(self, image_or_location, modifiers = None):
        return self._proxify(super(GuiBender, self).double_click(image_or_location, modifiers))

    def mouse_down(self, image_or_location, button=GuiBender.LEFT_BUTTON):
        return self._proxify(super(GuiBender, self).mouse_down(image_or_location, button))

    def mouse_up(self, image_or_location, button=GuiBender.LEFT_BUTTON):
        return self._proxify(super(GuiBender, self).mouse_up(image_or_location, button))

    def drag_drop(self, src_image_or_location, dst_image_or_location, modifiers = None):
        return self._proxify(super(GuiBender, self).drag_drop(src_image_or_location,
                                                              dst_image_or_location, modifiers))

    def drag(self, image_or_location, modifiers = None):
        return self._proxify(super(GuiBender, self).drag(image_or_location, modifiers))

    def drop_at(self, image_or_location, modifiers = None):
        return self._proxify(super(GuiBender, self).drop_at(image_or_location, modifiers))

    def press(self, keys):
        return self._proxify(super(GuiBender, self).press(keys))

    def press_at(self, image_or_location=None, keys=[]):
        return self._proxify(super(GuiBender, self).press_at(image_or_location, keys))

    def type_text(self, text, modifiers=None):
        return self._proxify(super(GuiBender, self).type_text(text, modifiers))

    def type_at(self, image_or_location=None, text='', modifiers=None):
        return self._proxify(super(GuiBender, self).type_at(image_or_location, text, modifiers))
