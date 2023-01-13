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
Remote guibot interface for proxy operations using remote visual objects.

Frontend with serialization compatible API allowing the use of PyRO modified
:py:class:`guibot.GuiBot` object (creating and running the same object
remotely and manipulating it locally). All the methods delegate their calls to
this object with some additional postprocessing to make the execution remote so
for information about the API please refer to it and :py:class:`region.Region`.


INTERFACE
------------------------------------------------------

"""

import re

try:
    import Pyro5 as pyro
except ImportError:
    import Pyro4 as pyro

from . import errors
from .guibot import GuiBot


def serialize_custom_error(class_obj):
    """
    Serialization method for the :py:class:`errors.UnsupportedBackendError`
    which was chosen just as a sample.

    :param class_obj: class object for the serialized error class
    :type class_obj: classobj
    :returns: serialization dictionary with the class name, arguments, and attributes
    :rtype: {str, str or getset_descriptor or dictproxy}
    """
    serialized = {}
    serialized["__class__"] = re.search("<class '(.+)'>", str(type(class_obj))).group(1)
    serialized["args"] = class_obj.args
    serialized["attributes"] = class_obj.__dict__
    return serialized


def register_exception_serialization():
    """
    We put here any exceptions that are too complicated for the default serialization
    and define their serialization methods.

    .. note:: This would not be needed if we were using the Pickle serializer but its
        security problems at the moment made us prefer the serpent serializer paying
        for it with some extra setup steps and functions below.
    """
    for exception in [errors.UnsupportedBackendError]:
        pyro.util.SerializerBase.register_class_to_dict(exception, serialize_custom_error)


class GuiBotProxy(GuiBot):
    """
    The proxy guibot object is just a wrapper around the actual guibot
    object that takes care of returning easily serializable PyRO proxy objects
    instead of the real ones or their serialized copies.

    It allows you to move the mouse, type text and do any other GuiBot action
    from code which is executed on another machine somewhere on the network.
    """

    def __init__(self, dc=None, cv=None):
        """Build a proxy guibot object of the original main guibot object."""
        super(GuiBotProxy, self).__init__(dc=dc, cv=cv)
        # NOTE: the following attribute is set by PyRO when registering
        # this as a remote object
        self._pyroDaemon = None
        # register exceptions as an extra step
        register_exception_serialization()

    def _proxify(self, obj):
        if isinstance(obj, (int, float, bool, str)) or obj is None:
            return obj
        if obj not in self._pyroDaemon.objectsById.values():
            self._pyroDaemon.register(obj)
        return obj

    def nearby(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).nearby(*args, **kwargs))

    def above(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).above(*args, **kwargs))

    def below(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).below(*args, **kwargs))

    def left(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).left(*args, **kwargs))

    def right(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).right(*args, **kwargs))

    def find(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).find(*args, **kwargs))

    def find_all(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        matches = super(GuiBotProxy, self).find_all(*args, **kwargs)
        proxified = []
        for match in matches:
            proxified.append(self._proxify(match))
        return proxified

    def sample(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).sample(*args, **kwargs))

    def exists(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).exists(*args, **kwargs))

    def wait(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).wait(*args, **kwargs))

    def wait_vanish(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).wait_vanish(*args, **kwargs))

    def idle(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).idle(*args, **kwargs))

    def hover(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).hover(*args, **kwargs))

    def click(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).click(*args, **kwargs))

    def right_click(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).right_click(*args, **kwargs))

    def middle_click(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).middle_click(*args, **kwargs))

    def double_click(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).double_click(*args, **kwargs))

    def multi_click(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).multi_click(*args, **kwargs))

    def click_expect(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).click_expect(*args, **kwargs))

    def click_vanish(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).click_vanish(*args, **kwargs))

    def click_at_index(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).click_at_index(*args, **kwargs))

    def mouse_down(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).mouse_down(*args, **kwargs))

    def mouse_up(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).mouse_up(*args, **kwargs))

    def mouse_scroll(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).mouse_scroll(*args, **kwargs))

    def drag_drop(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).drag_drop(*args, **kwargs))

    def drag_from(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).drag_from(*args, **kwargs))

    def drop_at(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).drop_at(*args, **kwargs))

    def press_keys(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).press_keys(*args, **kwargs))

    def press_at(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).press_at(*args, **kwargs))

    def press_expect(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).press_expect(*args, **kwargs))

    def press_vanish(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).press_vanish(*args, **kwargs))

    def type_text(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).type_text(*args, **kwargs))

    def type_at(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).type_at(*args, **kwargs))

    def click_at(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).click_at(*args, **kwargs))

    def fill_at(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).fill_at(*args, **kwargs))

    def select_at(self, *args, **kwargs):
        """See :py:class:`guibot.guibot.GuiBot` and its inherited :py:class:`guibot.region.Region` for details."""
        return self._proxify(super(GuiBotProxy, self).select_at(*args, **kwargs))
